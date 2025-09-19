#!/usr/bin/env python3
"""
Optimized FastAPI backend for Volume Composites Dashboard
Features connection pooling, caching, and performance optimizations
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import asyncpg
from contextlib import asynccontextmanager
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from functools import lru_cache
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Global connection pool
db_pool = None

# Cache for frequently accessed data
cache = {
    'filter_options': {'data': None, 'timestamp': None, 'ttl': 300},  # 5 min TTL
    'summary_stats': {'data': None, 'timestamp': None, 'ttl': 60},    # 1 min TTL
}

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'database': os.getenv('DB_NAME', 'volume_composites'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password')
}

async def init_db_pool():
    """Initialize database connection pool"""
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            min_size=5,
            max_size=20,
            command_timeout=60,
            server_settings={
                'jit': 'off',  # Disable JIT for faster simple queries
                'application_name': 'volume_composites_api'
            }
        )
        logger.info(f"Database pool initialized with {db_pool.get_min_size()}-{db_pool.get_max_size()} connections")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")
        raise

async def close_db_pool():
    """Close database connection pool"""
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager"""
    await init_db_pool()
    yield
    await close_db_pool()

app = FastAPI(
    title="Volume Composites API", 
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def is_cache_valid(cache_key: str) -> bool:
    """Check if cached data is still valid"""
    cache_entry = cache.get(cache_key)
    if not cache_entry or not cache_entry['data'] or not cache_entry['timestamp']:
        return False
    
    age = datetime.now() - cache_entry['timestamp']
    return age.total_seconds() < cache_entry['ttl']

def get_cached_data(cache_key: str) -> Optional[Any]:
    """Get data from cache if valid"""
    if is_cache_valid(cache_key):
        return cache[cache_key]['data']
    return None

def set_cached_data(cache_key: str, data: Any):
    """Store data in cache with timestamp"""
    cache[cache_key] = {
        'data': data,
        'timestamp': datetime.now(),
        'ttl': cache[cache_key]['ttl']
    }

async def get_db_connection():
    """Get database connection from pool"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database pool not initialized")
    return await db_pool.acquire()

async def release_db_connection(conn):
    """Release database connection back to pool"""
    if db_pool:
        await db_pool.release(conn)

# Pydantic models with validation
class DateFilter(BaseModel):
    operator: str  # 'equals', 'greaterThan', 'lessThan', 'between'
    startDate: str  # ISO date string
    endDate: Optional[str] = None  # ISO date string, only for 'between' operator

class FilterRequest(BaseModel):
    sbaClassification: Optional[List[str]] = []
    lineOfBusiness: Optional[List[str]] = []
    commitmentSizeGroup: Optional[List[str]] = []
    customCommitmentRanges: Optional[List[Dict[str, Any]]] = []
    riskGroup: Optional[List[str]] = []
    bankId: Optional[List[str]] = []
    region: Optional[List[str]] = []
    naicsGrpName: Optional[List[str]] = []
    dateFilters: Optional[List[DateFilter]] = []

class QueryRequest(BaseModel):
    filters: FilterRequest
    limit: Optional[int] = 1000
    
    class Config:
        validate_assignment = True

# Optimized query builders
def build_where_conditions(filters: FilterRequest) -> tuple[List[str], List[Any]]:
    """Build WHERE conditions and parameters for queries"""
    conditions = []
    params = []
    
    # SBA Classification
    if filters.sbaClassification:
        sba_conditions = []
        for classification in filters.sbaClassification:
            if classification.lower() == 'sba':
                sba_conditions.append("lineofbusinessid = $" + str(len(params) + 1))
                params.append('12')
            elif classification.lower() == 'non-sba':
                sba_conditions.append("lineofbusinessid != $" + str(len(params) + 1))
                params.append('12')
        if sba_conditions:
            conditions.append(f"({' OR '.join(sba_conditions)})")
    
    # Line of Business
    if filters.lineOfBusiness:
        lob_ids = [lob.split(' - ')[0] for lob in filters.lineOfBusiness]
        placeholders = [f"${i+len(params)+1}" for i in range(len(lob_ids))]
        conditions.append(f"lineofbusinessid = ANY(ARRAY[{','.join(placeholders)}])")
        params.extend(lob_ids)
    
    # Other filters with optimized IN clauses
    filter_mappings = {
        'commitmentSizeGroup': 'commitmentsizegroup',
        'riskGroup': 'riskgroupdesc', 
        'bankId': 'bankid',
        'region': 'region',
        'naicsGrpName': 'naicsgrpname'
    }
    
    for filter_attr, db_column in filter_mappings.items():
        filter_values = getattr(filters, filter_attr, None)
        if filter_values:
            placeholders = [f"${i+len(params)+1}" for i in range(len(filter_values))]
            conditions.append(f"{db_column} = ANY(ARRAY[{','.join(placeholders)}])")
            params.extend(filter_values)
    
    # Date filters
    if filters.dateFilters:
        for date_filter in filters.dateFilters:
            try:
                start_date = datetime.fromisoformat(date_filter.startDate.replace('Z', '+00:00'))
                start_date_key = int(start_date.strftime('%Y%m%d'))
                
                if date_filter.operator == "equals":
                    conditions.append(f"processingdatekey = ${len(params)+1}")
                    params.append(start_date_key)
                elif date_filter.operator == "greaterThan":
                    conditions.append(f"processingdatekey >= ${len(params)+1}")
                    params.append(start_date_key)
                elif date_filter.operator == "lessThan":
                    conditions.append(f"processingdatekey <= ${len(params)+1}")
                    params.append(start_date_key)
                elif date_filter.operator == "between" and date_filter.endDate:
                    end_date = datetime.fromisoformat(date_filter.endDate.replace('Z', '+00:00'))
                    end_date_key = int(end_date.strftime('%Y%m%d'))
                    conditions.append(f"processingdatekey BETWEEN ${len(params)+1} AND ${len(params)+2}")
                    params.extend([start_date_key, end_date_key])
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing date filter: {e}")
                continue
    
    return conditions, params

# Optimized API Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Volume Composites API - Optimized",
        "version": "2.0.0",
        "status": "running",
        "features": ["connection_pooling", "caching", "async_queries"]
    }

@app.get("/health")
async def health_check():
    """Async health check endpoint with connection pool status"""
    try:
        conn = await get_db_connection()
        result = await conn.fetchval("SELECT 1")
        await release_db_connection(conn)
        
        pool_info = {
            "size": db_pool.get_size(),
            "min_size": db_pool.get_min_size(), 
            "max_size": db_pool.get_max_size(),
            "idle": db_pool.get_idle_size()
        }
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat(),
            "connection_pool": pool_info
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "error", 
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@app.get("/api/connection-status")
async def connection_status():
    """Check database connection status for frontend"""
    try:
        conn = await get_db_connection()
        
        # Get basic info in a single query for efficiency
        query = """
        SELECT 
            COUNT(*) as record_count,
            MAX(processingdatekey) as max_date
        FROM analytics_data
        """
        
        result = await conn.fetchrow(query)
        await release_db_connection(conn)
        
        return {
            "isConnected": True,
            "error": None,
            "lastConnectionTime": datetime.now().isoformat(),
            "recordCount": result['record_count'],
            "maxDate": str(result['max_date']) if result['max_date'] else None
        }
        
    except Exception as e:
        logger.error(f"Connection status check failed: {e}")
        return {
            "isConnected": False,
            "error": f"Database query error: {str(e)}",
            "lastConnectionTime": None
        }

@app.get("/api/filter-options")
async def get_filter_options():
    """Get all available filter options from database with caching"""
    # Check cache first
    cached_data = get_cached_data('filter_options')
    if cached_data:
        logger.info("Returning cached filter options")
        return cached_data
    
    try:
        conn = await get_db_connection()
        
        # Optimized single query to get all filter options
        query = """
        WITH filter_data AS (
            SELECT DISTINCT 
                lineofbusinessid,
                lineofbusiness,
                commitmentsizegroup,
                riskgroupdesc,
                bankid,
                region,
                naicsgrpname
            FROM analytics_data 
            WHERE lineofbusinessid IS NOT NULL
        )
        SELECT 
            array_agg(DISTINCT lineofbusinessid ORDER BY lineofbusinessid) FILTER (WHERE lineofbusinessid IS NOT NULL) as lob_ids,
            array_agg(DISTINCT lineofbusiness ORDER BY lineofbusiness) FILTER (WHERE lineofbusiness IS NOT NULL) as lob_names,
            array_agg(DISTINCT commitmentsizegroup ORDER BY commitmentsizegroup) FILTER (WHERE commitmentsizegroup IS NOT NULL) as size_groups,
            array_agg(DISTINCT riskgroupdesc ORDER BY riskgroupdesc) FILTER (WHERE riskgroupdesc IS NOT NULL) as risk_groups,
            array_agg(DISTINCT bankid ORDER BY bankid) FILTER (WHERE bankid IS NOT NULL) as bank_ids,
            array_agg(DISTINCT region ORDER BY region) FILTER (WHERE region IS NOT NULL) as regions,
            array_agg(DISTINCT naicsgrpname ORDER BY naicsgrpname) FILTER (WHERE naicsgrpname IS NOT NULL) as naics_names
        FROM filter_data
        """
        
        result = await conn.fetchrow(query)
        await release_db_connection(conn)
        
        # Build filter options response
        filter_options = {
            "sbaClassification": ["SBA", "Non-SBA"],
            "commitmentSizeGroup": result['size_groups'] or [],
            "riskGroup": result['risk_groups'] or [],
            "bankId": result['bank_ids'] or [], 
            "region": result['regions'] or [],
            "naicsGrpName": result['naics_names'] or []
        }
        
        # Special handling for line of business to combine ID and name
        lob_ids = result['lob_ids'] or []
        lob_names = result['lob_names'] or []
        
        # Create a mapping of IDs to names
        lob_name_map = {}
        if lob_names:
            # This is a simplified approach - in a real scenario you'd need proper joining
            for i, lob_id in enumerate(lob_ids):
                if i < len(lob_names) and lob_names[i]:
                    lob_name_map[lob_id] = lob_names[i]
        
        filter_options["lineOfBusiness"] = [
            f"{lob_id} - {lob_name_map.get(lob_id, '')}" if lob_name_map.get(lob_id) else str(lob_id)
            for lob_id in lob_ids
        ]
        
        # Cache the result
        set_cached_data('filter_options', filter_options)
        logger.info("Filter options cached successfully")
        
        return filter_options
        
    except Exception as e:
        logger.error(f"Error fetching filter options: {e}")
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}") from e

@app.post("/api/query")
async def execute_query(request: QueryRequest):
    """Execute optimized filtered query against the database"""
    try:
        # Use optimized query builder
        where_conditions, params = build_where_conditions(request.filters)
        
        # Build the main query with proper column selection
        base_query = """
        SELECT 
            processingdatekey,
            commitmentamt,
            outstandingamt,
            region,
            naicsgrpname,
            commitmentsizegroup,
            riskgroupdesc,
            lineofbusinessid,
            lineofbusiness,
            bankid,
            maturitytermmonths,
            spreadbps,
            yieldpct
        FROM analytics_data
        """
        
        if where_conditions:
            base_query += f" WHERE {' AND '.join(where_conditions)}"
        
        base_query += " ORDER BY processingdatekey DESC, commitmentamt DESC"
        
        if request.limit:
            base_query += f" LIMIT ${len(params)+1}"
            params.append(request.limit)
        
        # Execute optimized query
        results = await conn.fetch(base_query, *params)
        await release_db_connection(conn)
        
        # Convert to list of dictionaries with optimized serialization
        data = [
            {
                "processingdatekey": record['processingdatekey'],
                "commitmentamt": float(record['commitmentamt']) if record['commitmentamt'] is not None else None,
                "outstandingamt": float(record['outstandingamt']) if record['outstandingamt'] is not None else None,
                "region": record['region'],
                "naicsgrpname": record['naicsgrpname'],
                "commitmentsizegroup": record['commitmentsizegroup'],
                "riskgroupdesc": record['riskgroupdesc'],
                "lineofbusinessid": record['lineofbusinessid'],
                "lineofbusiness": record['lineofbusiness'],
                "bankid": record['bankid'],
                "maturitytermmonths": record['maturitytermmonths'],
                "spreadbps": float(record['spreadbps']) if record['spreadbps'] is not None else None,
                "yieldpct": float(record['yieldpct']) if record['yieldpct'] is not None else None
            }
            for record in results
        ]
        
        logger.info(f"Query executed successfully, returned {len(data)} records")
        
        return {
            "success": True,
            "data": data,
            "totalRecords": len(data),
            "query": {
                "filters": request.filters.model_dump(),
                "limit": request.limit
            }
        }
        
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}") from e

@app.get("/api/analytics-data")
async def get_analytics_data(limit: Optional[int] = None):
    """Get aggregated analytics data (time series) with optimized query"""
    try:
        conn = await get_db_connection()
        
        query = "SELECT * FROM aggregated_analytics ORDER BY processingdatekey"
        params = []
        
        if limit:
            query += " LIMIT $1"
            params.append(limit)
        
        results = await conn.fetch(query, *params)
        await release_db_connection(conn)
        
        # Optimized data conversion
        data = [
            {
                key: float(value) if isinstance(value, (int, float)) and value is not None else value
                for key, value in dict(record).items()
            }
            for record in results
        ]
        
        logger.info(f"Analytics data query returned {len(data)} records")
        
        return {
            "success": True,
            "data": data,
            "totalRecords": len(data)
        }
        
    except Exception as e:
        logger.error(f"Analytics data query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}") from e

@app.get("/api/summary-stats")
async def get_summary_stats():
    """Get summary statistics with caching"""
    # Check cache first
    cached_data = get_cached_data('summary_stats')
    if cached_data:
        logger.info("Returning cached summary stats")
        return cached_data
    
    try:
        conn = await get_db_connection()
        
        # Optimized single query for all statistics
        query = """
        WITH stats AS (
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT processingdatekey) as unique_months,
                MIN(processingdatekey) as earliest_date,
                MAX(processingdatekey) as latest_date,
                SUM(commitmentamt) as total_commitment,
                AVG(commitmentamt) as avg_commitment,
                COUNT(DISTINCT region) as unique_regions,
                COUNT(DISTINCT lineofbusinessid) as unique_lobs,
                COUNT(DISTINCT bankid) as unique_banks
            FROM analytics_data
            WHERE commitmentamt IS NOT NULL
        ),
        latest_month AS (
            SELECT 
                processingdatekey,
                COUNT(*) as deals,
                SUM(commitmentamt) as total_commitment,
                SUM(outstandingamt) as total_outstanding
            FROM analytics_data
            WHERE processingdatekey = (SELECT MAX(processingdatekey) FROM analytics_data)
            GROUP BY processingdatekey
        )
        SELECT 
            s.*,
            COALESCE(l.processingdatekey, 0) as latest_month_date,
            COALESCE(l.deals, 0) as latest_month_deals,
            COALESCE(l.total_commitment, 0) as latest_month_commitment,
            COALESCE(l.total_outstanding, 0) as latest_month_outstanding
        FROM stats s
        LEFT JOIN latest_month l ON true
        """
        
        result = await conn.fetchrow(query)
        await release_db_connection(conn)
        
        summary_data = {
            "success": True,
            "summary": {
                "totalRecords": result['total_records'],
                "uniqueMonths": result['unique_months'],
                "dateRange": {
                    "earliest": str(result['earliest_date']),
                    "latest": str(result['latest_date'])
                },
                "totals": {
                    "commitment": float(result['total_commitment']) if result['total_commitment'] else 0,
                    "averageCommitment": float(result['avg_commitment']) if result['avg_commitment'] else 0
                },
                "uniqueCounts": {
                    "regions": result['unique_regions'],
                    "lineOfBusiness": result['unique_lobs'],
                    "banks": result['unique_banks']
                }
            },
            "latestMonth": {
                "date": str(result['latest_month_date']) if result['latest_month_date'] else None,
                "deals": result['latest_month_deals'],
                "totalCommitment": float(result['latest_month_commitment']) if result['latest_month_commitment'] else 0,
                "totalOutstanding": float(result['latest_month_outstanding']) if result['latest_month_outstanding'] else 0
            }
        }
        
        # Cache the result
        set_cached_data('summary_stats', summary_data)
        logger.info("Summary stats cached successfully")
        
        return summary_data
        
    except Exception as e:
        logger.error(f"Summary stats query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}") from e

# Cache management endpoints
@app.post("/api/cache/clear")
async def clear_cache():
    """Clear all cached data"""
    global cache
    cache = {
        'filter_options': {'data': None, 'timestamp': None, 'ttl': 300},
        'summary_stats': {'data': None, 'timestamp': None, 'ttl': 60},
    }
    logger.info("All cache cleared")
    return {"success": True, "message": "Cache cleared successfully"}

@app.get("/api/cache/status")
async def cache_status():
    """Get cache status information"""
    status = {}
    for key, entry in cache.items():
        status[key] = {
            "cached": entry['data'] is not None,
            "timestamp": entry['timestamp'].isoformat() if entry['timestamp'] else None,
            "valid": is_cache_valid(key),
            "ttl": entry['ttl']
        }
    return {"success": True, "cache_status": status}

# Legacy analysis endpoint placeholder
@app.post("/api/execute-capped-analysis")
async def execute_capped_analysis(request: QueryRequest):
    """Placeholder for legacy analysis endpoint"""
    return {
        "success": False,
        "error": "Legacy analysis endpoint disabled in optimized version",
        "message": "Use the new /api/query endpoint for data retrieval"
    }

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Starting optimized Volume Composites API server...")
    logger.info(f"📊 Database: {DB_CONFIG['database']} @ {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    logger.info(f"🌐 Frontend CORS enabled for: http://localhost:3000, http://localhost:5173")
    logger.info(f"⚡ Features: Connection pooling, caching, async queries")
    
    uvicorn.run(
        "backend_api:app",
        host="0.0.0.0",
        port=int(os.getenv('API_PORT', '8000')),
        reload=True,
        log_level="info"
    )
            lob_ids = [lob.split(' - ')[0] if ' - ' in lob else lob for lob in request.filters.lineOfBusiness]
            placeholders = ','.join(['%s'] * len(lob_ids))
            where_conditions.append(f'lineofbusinessid IN ({placeholders})')
            params.extend(lob_ids)
        
        if request.filters.commitmentSizeGroup:
            placeholders = ','.join(['%s'] * len(request.filters.commitmentSizeGroup))
            where_conditions.append(f'commitmentsizegroup IN ({placeholders})')
            params.extend(request.filters.commitmentSizeGroup)
        
        if request.filters.riskGroup:
            placeholders = ','.join(['%s'] * len(request.filters.riskGroup))
            where_conditions.append(f'riskgroupdesc IN ({placeholders})')
            params.extend(request.filters.riskGroup)
        
        if request.filters.region:
            placeholders = ','.join(['%s'] * len(request.filters.region))
            where_conditions.append(f'region IN ({placeholders})')
            params.extend(request.filters.region)
        
        if request.filters.naicsGrpName:
            placeholders = ','.join(['%s'] * len(request.filters.naicsGrpName))
            where_conditions.append(f'naicsgrpname IN ({placeholders})')
            params.extend(request.filters.naicsGrpName)
        
        # Handle date filters (ProcessingDateKey only)
        if request.filters.dateFilters:
            for date_filter in request.filters.dateFilters:
                try:
                    # Convert ISO date string to YYYYMMDD format
                    start_date = datetime.fromisoformat(date_filter.startDate.replace('Z', '+00:00'))
                    start_date_key = int(start_date.strftime('%Y%m%d'))
                    
                    if date_filter.operator == "equals":
                        where_conditions.append("processingdatekey = %s")
                        params.append(start_date_key)
                    elif date_filter.operator == "greaterThan":
                        where_conditions.append("processingdatekey >= %s")
                        params.append(start_date_key)
                    elif date_filter.operator == "lessThan":
                        where_conditions.append("processingdatekey <= %s")
                        params.append(start_date_key)
                    elif date_filter.operator == "between" and date_filter.endDate:
                        end_date = datetime.fromisoformat(date_filter.endDate.replace('Z', '+00:00'))
                        end_date_key = int(end_date.strftime('%Y%m%d'))
                        where_conditions.append("processingdatekey BETWEEN %s AND %s")
                        params.extend([start_date_key, end_date_key])
                except (ValueError, TypeError) as e:
                    print(f"Error parsing date filter: {e}")
                    continue
        
        # Build the query to get raw data for analysis
        base_query = """
        SELECT 
            processingdatekey,
            commitmentamt,
            outstandingamt,
            bankid
        FROM analytics_data
        """
        
        if where_conditions:
            base_query += f" WHERE {' AND '.join(where_conditions)}"
        
        base_query += ' ORDER BY processingdatekey, bankid'
        
        # Execute query and get raw data
        cursor = conn.cursor()
        cursor.execute(base_query, params)
        columns = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()
        
        # Convert to DataFrame with proper column names
        df_data = []
        column_mapping = {
            'processingdatekey': 'ProcessingDateKey',
            'commitmentamt': 'CommitmentAmt', 
            'outstandingamt': 'OutstandingAmt',
            'bankid': 'BankID'
        }
        
        for row in results:
            row_dict = {}
            for i, value in enumerate(row):
                col_name = columns[i].lower()
                mapped_name = column_mapping.get(col_name, columns[i])
                if hasattr(value, 'quantize'):  # Decimal type
                    row_dict[mapped_name] = float(value) if value is not None else None
                else:
                    row_dict[mapped_name] = value
            df_data.append(row_dict)
        
        cursor.close()
        conn.close()
        conn = None
        
        if not df_data:
            return {
                "success": False,
                "error": "No data found for the selected filters",
                "data": []
            }
        
        print(f"Retrieved {len(df_data)} rows for analysis")
        
        # Convert to DataFrame for processing
        df = pd.DataFrame(df_data)
        
        # Run the setup_groups analysis to get capped differences
        import polars as pl
        df_polars = pl.from_pandas(df)
        
        print("Running setup_groups analysis...")
        # Get the capped analysis results
        ca_pivot, oa_pivot, deals_pivot = setup_groups(df_polars)
        
        # Extract the percentage differences (these are the "capped" results)
        ca_perc_diff = ca_pivot["perc_diff"]
        oa_perc_diff = oa_pivot["perc_diff"] 
        deals_perc_diff = deals_pivot["perc_diff"]
        
        print("Running testCappedvsUncapped analysis...")
        # Run the testCappedvsUncapped analysis
        result_df = testCappedvsUncapped(
            df_polars,
            ca_perc_diff,
            oa_perc_diff, 
            deals_perc_diff,
            None  # Don't save to file
        )
        
        # Convert result to JSON format
        if hasattr(result_df, 'to_dicts'):
            analysis_results = result_df.to_dicts()
        else:
            analysis_results = result_df.to_dict('records')
        
        # Format ProcessingDateKey as YYYYMMDD string and handle NaN values
        formatted_results = []
        for record in analysis_results:
            formatted_record = {}
            for key, value in record.items():
                # Handle NaN values
                if value is not None and hasattr(value, '__class__') and 'float' in str(value.__class__):
                    import math
                    if math.isnan(value) or math.isinf(value):
                        value = None
                
                formatted_record[key] = value
            
            # Format dates as YYYYMMDD strings
            if 'ProcessingDateKey' in formatted_record and formatted_record['ProcessingDateKey']:
                date_int = int(formatted_record['ProcessingDateKey'])
                formatted_record['ProcessingDateKey'] = str(date_int)
            if 'ProcessingDateKeyPrior' in formatted_record and formatted_record['ProcessingDateKeyPrior']:
                date_int = int(formatted_record['ProcessingDateKeyPrior'])
                formatted_record['ProcessingDateKeyPrior'] = str(date_int) if date_int != 0 else '0'
                
            formatted_results.append(formatted_record)
        
        return {
            "success": True,
            "data": formatted_results,
            "totalRecords": len(formatted_results),
            "analysis_type": "capped_vs_uncapped",
            "filters_applied": request.filters.model_dump()
        }
        
    except (ImportError, ValueError, psycopg2.Error, AttributeError) as e:
        import traceback
        print(f"Error in capped analysis: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}") from e

@app.get("/api/summary-stats")
def get_summary_stats():
    """Get summary statistics from the database"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cursor = conn.cursor()
        
        # Get overall statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT ProcessingDateKey) as unique_months,
                MIN(ProcessingDateKey) as earliest_date,
                MAX(ProcessingDateKey) as latest_date,
                SUM(CommitmentAmt) as total_commitment,
                AVG(CommitmentAmt) as avg_commitment,
                COUNT(DISTINCT Region) as unique_regions,
                COUNT(DISTINCT LineofBusinessId) as unique_lobs,
                COUNT(DISTINCT BankID) as unique_banks
            FROM analytics_data
            WHERE CommitmentAmt IS NOT NULL
        """)
        
        stats = cursor.fetchone()
        
        # Get latest month statistics
        cursor.execute("""
            SELECT 
                ProcessingDateKey,
                COUNT(*) as deals,
                SUM(CommitmentAmt) as total_commitment,
                SUM(OutstandingAmt) as total_outstanding
            FROM analytics_data
            WHERE ProcessingDateKey = (SELECT MAX(ProcessingDateKey) FROM analytics_data)
            GROUP BY ProcessingDateKey
        """)
        
        latest_month = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "summary": {
                "totalRecords": stats[0],
                "uniqueMonths": stats[1],
                "dateRange": {
                    "earliest": str(stats[2]),
                    "latest": str(stats[3])
                },
                "totals": {
                    "commitment": float(stats[4]) if stats[4] else 0,
                    "averageCommitment": float(stats[5]) if stats[5] else 0
                },
                "uniqueCounts": {
                    "regions": stats[6],
                    "lineOfBusiness": stats[7],
                    "banks": stats[8]
                }
            },
            "latestMonth": {
                "date": str(latest_month[0]) if latest_month else None,
                "deals": latest_month[1] if latest_month else 0,
                "totalCommitment": float(latest_month[2]) if latest_month and latest_month[2] else 0,
                "totalOutstanding": float(latest_month[3]) if latest_month and latest_month[3] else 0
            }
        }
        
    except psycopg2.Error as e:
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}") from e

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Volume Composites API server...")
    print(f"📊 Database: {DB_CONFIG['database']} @ {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"🌐 Frontend CORS enabled for: http://localhost:3000, http://localhost:5173")
    
    uvicorn.run(
        "backend_api:app",
        host="0.0.0.0",
        port=int(os.getenv('API_PORT', '8000')),
        reload=True
    )
