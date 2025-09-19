#!/usr/bin/env python3
"""
Updated FastAPI backend for Volume Composites Dashboard
Connects to PostgreSQL database created from sample.csv
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import psycopg2
import pandas as pd
import os
from datetime import datetime
from dotenv import load_dotenv
import polars as pl

# Load environment variables
load_dotenv()

app = FastAPI(title="Volume Composites API", version="1.0.0")

# CORS middleware for frontend connection
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

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'database': os.getenv('DB_NAME', 'volume_composites'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password')
}

def get_db_connection():
    """Create database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_session(readonly=True)
        return conn
    except psycopg2.Error:
        # Prefer explicit error handling in endpoints
        return None

# Pydantic models
class DateFilterModel(BaseModel):
    operator: str  # 'equals' | 'greaterThan' | 'lessThan' | 'between'
    startDate: str  # ISO date string
    endDate: Optional[str] = None  # ISO date string, only for 'between'


class FilterRequest(BaseModel):
    sbaClassification: Optional[List[str]] = []
    lineOfBusiness: Optional[List[str]] = []
    commitmentSizeGroup: Optional[List[str]] = []
    customCommitmentRanges: Optional[List[Dict[str, Any]]] = []
    riskGroup: Optional[List[str]] = []
    bankId: Optional[List[str]] = []
    region: Optional[List[str]] = []
    naicsGrpName: Optional[List[str]] = []
    dateFilters: Optional[List[DateFilterModel]] = []

class QueryRequest(BaseModel):
    filters: FilterRequest
    limit: Optional[int] = 1000

# API Endpoints

def _build_where_conditions_from_filters(filters: FilterRequest) -> tuple[list[str], list[Any]]:
    """Convert FilterRequest into SQL WHERE conditions and parameters.

    Returns a tuple: (conditions, params)
    """
    where_conditions: list[str] = []
    params: list[Any] = []

    # SBA classification (LOB id '12' assumed to be SBA)
    if filters.sbaClassification:
        sba_conditions: list[str] = []
        for classification in filters.sbaClassification:
            cls = classification.lower()
            if cls == 'sba':
                sba_conditions.append('"LineofBusinessId" = %s')
                params.append('12')
            elif cls == 'non-sba':
                sba_conditions.append('"LineofBusinessId" != %s')
                params.append('12')
        if sba_conditions:
            where_conditions.append(f"({' OR '.join(sba_conditions)})")

    # Line of business (supports values like "11 - Commercial" and raw IDs)
    if filters.lineOfBusiness:
        lob_ids = [lob.split(' - ')[0] if ' - ' in lob else lob for lob in filters.lineOfBusiness]
        placeholders = ','.join(['%s'] * len(lob_ids))
        where_conditions.append(f'"LineofBusinessId" IN ({placeholders})')
        params.extend(lob_ids)

    # Commitment size group
    if filters.commitmentSizeGroup:
        placeholders = ','.join(['%s'] * len(filters.commitmentSizeGroup))
        where_conditions.append(f'"CommitmentSizeGroup" IN ({placeholders})')
        params.extend(filters.commitmentSizeGroup)

    # Risk group
    if filters.riskGroup:
        placeholders = ','.join(['%s'] * len(filters.riskGroup))
        where_conditions.append(f'"RiskGroupDesc" IN ({placeholders})')
        params.extend(filters.riskGroup)

    # Bank ID
    if filters.bankId:
        placeholders = ','.join(['%s'] * len(filters.bankId))
        where_conditions.append(f'"BankID" IN ({placeholders})')
        params.extend(filters.bankId)

    # Region
    if filters.region:
        placeholders = ','.join(['%s'] * len(filters.region))
        where_conditions.append(f'"Region" IN ({placeholders})')
        params.extend(filters.region)

    # NAICS group name
    if filters.naicsGrpName:
        placeholders = ','.join(['%s'] * len(filters.naicsGrpName))
        where_conditions.append(f'"NAICSGrpName" IN ({placeholders})')
        params.extend(filters.naicsGrpName)

    # Custom commitment ranges
    if filters.customCommitmentRanges:
        range_conditions: list[str] = []
        for range_filter in filters.customCommitmentRanges:
            range_conditions.append('("CommitmentAmt" >= %s AND "CommitmentAmt" <= %s)')
            params.extend([range_filter['min'], range_filter['max']])
        if range_conditions:
            where_conditions.append(f"({' OR '.join(range_conditions)})")

    # Date filters on ProcessingDateKey: expects ISO strings; convert to YYYYMMDD integer
    if filters.dateFilters:
        date_conditions: list[str] = []
        for df in filters.dateFilters:
            try:
                start_str = df.startDate.replace('Z', '+00:00') if isinstance(df.startDate, str) else df.startDate
                end_str = df.endDate.replace('Z', '+00:00') if (df.endDate and isinstance(df.endDate, str)) else df.endDate
                start_int = int(datetime.fromisoformat(start_str).strftime('%Y%m%d'))
                end_int = int(datetime.fromisoformat(end_str).strftime('%Y%m%d')) if end_str else None
            except (ValueError, TypeError, AttributeError):
                continue

            op = (df.operator or '').lower()
            if op == 'equals':
                date_conditions.append('"ProcessingDateKey" = %s')
                params.append(start_int)
            elif op == 'greaterthan':
                date_conditions.append('"ProcessingDateKey" >= %s')
                params.append(start_int)
            elif op == 'lessthan':
                date_conditions.append('"ProcessingDateKey" <= %s')
                params.append(start_int)
            elif op == 'between' and end_int is not None:
                date_conditions.append('(\"ProcessingDateKey\" BETWEEN %s AND %s)'.replace('\\"','"'))
                params.extend([start_int, end_int])

        if date_conditions:
            where_conditions.append(f"({' AND '.join(date_conditions)})")

    return where_conditions, params

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Volume Composites API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            db_status = "connected"
        except psycopg2.Error:
            db_status = "error"
    else:
        db_status = "disconnected"
    
    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/connection-status")
def connection_status():
    """Check database connection status for frontend"""
    conn = get_db_connection()
    if not conn:
        return {
            "isConnected": False,
            "error": "Unable to connect to PostgreSQL database",
            "lastConnectionTime": None
        }
    
    try:
        cursor = conn.cursor()
        
        # Test query to get some basic info
        cursor.execute("SELECT COUNT(*) FROM cla_uat.mv_t_cla_input_full_upd")
        record_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT MAX("ProcessingDateKey") FROM cla_uat.mv_t_cla_input_full_upd')
        max_date = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return {
            "isConnected": True,
            "error": None,
            "lastConnectionTime": datetime.now().isoformat(),
            "recordCount": record_count,
            "maxDate": str(max_date) if max_date else None
        }

    except psycopg2.Error as e:
        if conn:
            conn.close()
        return {
            "isConnected": False,
            "error": f"Database query error: {str(e)}",
            "lastConnectionTime": None
        }

@app.get("/api/filter-options")
def get_filter_options():
    """Get all available filter options from database"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor()

        # Get distinct values for each filter type
        filter_queries = {
            "lineOfBusiness": '''
                SELECT DISTINCT "LineofBusinessId", "LineofBusiness" 
                FROM cla_uat.mv_t_cla_input_full_upd 
                WHERE "LineofBusinessId" IS NOT NULL 
                ORDER BY "LineofBusinessId"
            ''',
            "commitmentSizeGroup": '''
                SELECT DISTINCT "CommitmentSizeGroup" 
                FROM cla_uat.mv_t_cla_input_full_upd 
                WHERE "CommitmentSizeGroup" IS NOT NULL 
                ORDER BY "CommitmentSizeGroup"
            ''',
            "riskGroup": '''
                SELECT DISTINCT "RiskGroupDesc" 
                FROM cla_uat.mv_t_cla_input_full_upd 
                WHERE "RiskGroupDesc" IS NOT NULL 
                ORDER BY "RiskGroupDesc"
            ''',
            "bankId": '''
                SELECT DISTINCT "BankID" 
                FROM cla_uat.mv_t_cla_input_full_upd 
                WHERE "BankID" IS NOT NULL 
                ORDER BY "BankID"
            ''',
            "region": '''
                SELECT DISTINCT "Region" 
                FROM cla_uat.mv_t_cla_input_full_upd 
                WHERE "Region" IS NOT NULL 
                ORDER BY "Region"
            ''',
            "naicsGrpName": '''
                SELECT DISTINCT "NAICSGrpName"
                FROM cla_uat.mv_t_cla_input_full_upd 
                WHERE "NAICSGrpName" IS NOT NULL 
                ORDER BY "NAICSGrpName"
            '''
        }

        filter_options = {}

        # Add SBA classification options (hardcoded as they're based on logic)
        filter_options["sbaClassification"] = ["SBA", "Non-SBA"]

        # Execute queries and build filter options
        for filter_name, query in filter_queries.items():
            cursor.execute(query)
            results = cursor.fetchall()

            if filter_name == "lineOfBusiness":
                # Special handling for line of business to include both ID and name
                filter_options[filter_name] = [
                    f"{row[0]} - {row[1]}" if row[1] else str(row[0])
                    for row in results
                ]
            else:
                filter_options[filter_name] = [row[0] for row in results]

        cursor.close()
        conn.close()

        return filter_options

    except psycopg2.Error as e:
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}") from e


@app.post("/api/query")
def execute_query(request: QueryRequest):
    """Execute filtered query against the database"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor()

        # Build WHERE conditions based on filters
        where_conditions, params = _build_where_conditions_from_filters(request.filters)

        # Build the main query
        base_query = '''
        SELECT 
            "ProcessingDateKey",
            "CommitmentAmt",
            "OutstandingAmt",
            "Region",
            "NAICSGrpName",
            "CommitmentSizeGroup",
            "RiskGroupDesc",
            "LineofBusinessId",
            "LineofBusiness",
            "BankID",
            "MaturityTermMonths",
            "SpreadBPS",
            "YieldPct"
        FROM cla_uat.mv_t_cla_input_full_upd
        '''

        if where_conditions:
            base_query += f" WHERE {' AND '.join(where_conditions)}"

        base_query += ' ORDER BY "ProcessingDateKey" DESC, "CommitmentAmt" DESC'

        if request.limit:
            base_query += f" LIMIT {request.limit}"

        # Execute query
        cursor.execute(base_query, params)

        # Get column names
        columns = [desc[0] for desc in cursor.description]

        # Fetch results
        results = cursor.fetchall()

        # Convert to list of dictionaries
        data = []
        for row in results:
            row_dict = {}
            for i, value in enumerate(row):
                # Convert Decimal to float for JSON serialization
                if hasattr(value, 'quantize'):  # Decimal type
                    row_dict[columns[i]] = float(value) if value is not None else None
                else:
                    row_dict[columns[i]] = value
            data.append(row_dict)

        cursor.close()
        conn.close()
        return {
            "success": True,
            "data": data,
            "totalRecords": len(data),
            "query": {
                "filters": request.filters.model_dump(),
                "limit": request.limit
            }
        }

    except psycopg2.Error as e:
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}") from e

@app.get("/api/analytics-data")
def get_analytics_data(limit: Optional[int] = None):
    """Get aggregated analytics data (time series)"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor()

        query = 'SELECT * FROM aggregated_analytics ORDER BY "ProcessingDateKey"'

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()

        # Convert to list of dictionaries
        data = []
        for row in results:
            row_dict = {}
            for i, value in enumerate(row):
                # Convert Decimal to float for JSON serialization
                if hasattr(value, 'quantize'):  # Decimal type
                    row_dict[columns[i]] = float(value) if value is not None else None
                else:
                    row_dict[columns[i]] = value
            data.append(row_dict)

        cursor.close()
        conn.close()

        return {
            "success": True,
            "data": data,
            "totalRecords": len(data)
        }

    except psycopg2.Error as e:
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}") from e

@app.post("/api/test-analysis")
def test_analysis():
    """Test endpoint for debugging"""
    try:
        import importlib
        mod = importlib.import_module('main')
        getattr(mod, 'testCappedvsUncapped')
        return {"status": "success", "message": "Functions imported successfully"}
    except (ImportError, AttributeError) as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/execute-capped-analysis")
def execute_capped_analysis(request: QueryRequest):
    """Execute the testCappedvsUncapped analysis with filtered data"""
    conn = None
    try:
        import sys
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.append(current_dir)

        from main import testCappedvsUncapped, setup_groups as setup_groups, BusinessConfig
        # analysis functions imported

        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")

        # Build WHERE conditions based on filters
        where_conditions, params = _build_where_conditions_from_filters(request.filters)

        # Build the query to get raw data for analysis
        base_query = '''
        SELECT 
            "ProcessingDateKey",
            "CommitmentAmt",
            "OutstandingAmt",
            "BankID",
            "LineofBusinessId",
            "CommitmentSizeGroup", 
            "RiskGroupDesc",
            "Region",
            "NAICSGrpName"
        FROM cla_uat.mv_t_cla_input_full_upd
        '''

        if where_conditions:
            base_query += f" WHERE {' AND '.join(where_conditions)}"

        # Execute query and get raw data
        cursor = conn.cursor()
        cursor.execute(base_query, params)
        columns = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()

        # Convert to DataFrame with proper column names
        df_data = []
        column_mapping = {
            'ProcessingDateKey': 'ProcessingDateKey',
            'CommitmentAmt': 'CommitmentAmt',
            'OutstandingAmt': 'OutstandingAmt',
            'BankID': 'BankID'
        }

        for row in results:
            row_dict = {}
            for i, value in enumerate(row):
                col_name = columns[i]
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

        # Convert to DataFrame for processing
        df = pd.DataFrame(df_data)

        # Run the setup_groups analysis to get capped differences
        df_polars = pl.from_pandas(df)

        # Get the capped analysis results
        ca_pivot, oa_pivot, deals_pivot = setup_groups(
            df_polars,
            max_mom=BusinessConfig.MAX_MOM,
            min_mom=BusinessConfig.MIN_MOM,
            max_mom_high=BusinessConfig.MAX_MOM_HIGH,
            min_mom_high=BusinessConfig.MIN_MOM_HIGH,
            high_breach_perc=BusinessConfig.HIGH_BREACH_PERC
        )

        # Extract the percentage differences (these are the "capped" results)
        if hasattr(ca_pivot, 'collect'):
            ca_pivot = ca_pivot.collect()
        if hasattr(oa_pivot, 'collect'):
            oa_pivot = oa_pivot.collect()
        if hasattr(deals_pivot, 'collect'):
            deals_pivot = deals_pivot.collect()

        ca_perc_diff = ca_pivot["perc_diff"]
        oa_perc_diff = oa_pivot["perc_diff"]
        deals_perc_diff = deals_pivot["perc_diff"]

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

    except Exception as e:
        # log error
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

        stats_query = '''
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT "ProcessingDateKey") as unique_months,
                MIN("ProcessingDateKey") as earliest_date,
                MAX("ProcessingDateKey") as latest_date,
                SUM("CommitmentAmt") as total_commitment,
                AVG("CommitmentAmt") as avg_commitment,
                COUNT(DISTINCT "Region") as unique_regions,
                COUNT(DISTINCT "LineofBusinessId") as unique_lobs,
                COUNT(DISTINCT "BankID") as unique_banks
            FROM cla_uat.mv_t_cla_input_full_upd
            WHERE "CommitmentAmt" IS NOT NULL
        '''

        cursor.execute(stats_query)
        stats_row = cursor.fetchone()

        last_month_query = '''
            SELECT 
                "ProcessingDateKey",
                COUNT(*) as deals,
                SUM("CommitmentAmt") as total_commitment,
                SUM("OutstandingAmt")::float8 AS total_outstanding
            FROM cla_uat.mv_t_cla_input_full_upd
            WHERE "ProcessingDateKey" = (SELECT MAX("ProcessingDateKey") FROM cla_uat.mv_t_cla_input_full_upd)
            GROUP BY "ProcessingDateKey"
        '''

        cursor.execute(last_month_query)
        latest_row = cursor.fetchone()

        cursor.close()
        conn.close()

        summary_payload = {
            "totalRecords": int(stats_row[0]) if stats_row and stats_row[0] is not None else 0,
            "uniqueMonths": int(stats_row[1]) if stats_row and stats_row[1] is not None else 0,
            "dateRange": {
                "earliest": str(stats_row[2]) if stats_row and stats_row[2] is not None else None,
                "latest": str(stats_row[3]) if stats_row and stats_row[3] is not None else None,
            },
            "totals": {
                "commitment": float(stats_row[4]) if stats_row and stats_row[4] is not None else 0.0,
                "averageCommitment": float(stats_row[5]) if stats_row and stats_row[5] is not None else 0.0,
            },
            "uniqueCounts": {
                "regions": int(stats_row[6]) if stats_row and stats_row[6] is not None else 0,
                "lineOfBusiness": int(stats_row[7]) if stats_row and stats_row[7] is not None else 0,
                "banks": int(stats_row[8]) if stats_row and stats_row[8] is not None else 0,
            },
        }

        latest_payload = {
            "date": str(latest_row[0]) if latest_row and latest_row[0] is not None else None,
            "deals": int(latest_row[1]) if latest_row and latest_row[1] is not None else 0,
            "totalCommitment": float(latest_row[2]) if latest_row and latest_row[2] is not None else 0.0,
            "totalOutstanding": float(latest_row[3]) if latest_row and latest_row[3] is not None else 0.0,
        }

        return {
            "success": True,
            "data": {
                "summary": summary_payload,
                "latestMonth": latest_payload,
            },
        }

    except psycopg2.Error as e:
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}") from e

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Volume Composites API server...")
    print(f"📊 Database: {DB_CONFIG['database']} @ {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print("🌐 Frontend CORS enabled for: http://localhost:3000, http://localhost:5173")
    
    uvicorn.run(
        "backend_api:app",
        host="0.0.0.0",
        port=int(os.getenv('API_PORT', '8000')),
        reload=True
    )