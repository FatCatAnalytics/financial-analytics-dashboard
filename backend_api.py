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
import json
from dotenv import load_dotenv

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
        return conn
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        return None

# Pydantic models
class FilterRequest(BaseModel):
    sbaClassification: Optional[List[str]] = []
    lineOfBusiness: Optional[List[str]] = []
    commitmentSizeGroup: Optional[List[str]] = []
    customCommitmentRanges: Optional[List[Dict[str, Any]]] = []
    riskGroup: Optional[List[str]] = []
    bankId: Optional[List[str]] = []
    region: Optional[List[str]] = []
    naicsGrpName: Optional[List[str]] = []

class QueryRequest(BaseModel):
    filters: FilterRequest
    limit: Optional[int] = 1000

# API Endpoints

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
        except:
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
        cursor.execute("SELECT COUNT(*) FROM analytics_data")
        record_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT MAX(ProcessingDateKey) FROM analytics_data")
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
            "lineOfBusiness": """
                SELECT DISTINCT LineofBusinessId, LineofBusiness 
                FROM analytics_data 
                WHERE LineofBusinessId IS NOT NULL 
                ORDER BY LineofBusinessId
            """,
            "commitmentSizeGroup": """
                SELECT DISTINCT CommitmentSizeGroup 
                FROM analytics_data 
                WHERE CommitmentSizeGroup IS NOT NULL 
                ORDER BY CommitmentSizeGroup
            """,
            "riskGroup": """
                SELECT DISTINCT RiskGroupDesc 
                FROM analytics_data 
                WHERE RiskGroupDesc IS NOT NULL 
                ORDER BY RiskGroupDesc
            """,
            "bankId": """
                SELECT DISTINCT BankID 
                FROM analytics_data 
                WHERE BankID IS NOT NULL 
                ORDER BY BankID
            """,
            "region": """
                SELECT DISTINCT Region 
                FROM analytics_data 
                WHERE Region IS NOT NULL 
                ORDER BY Region
            """,
            "naicsGrpName": """
                SELECT DISTINCT NAICSGrpName 
                FROM analytics_data 
                WHERE NAICSGrpName IS NOT NULL 
                ORDER BY NAICSGrpName
            """
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
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")

@app.post("/api/query")
def execute_query(request: QueryRequest):
    """Execute filtered query against the database"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cursor = conn.cursor()
        
        # Build WHERE conditions based on filters
        where_conditions = []
        params = []
        
        if request.filters.lineOfBusiness:
            # Extract just the ID part (before the " - " separator)
            lob_ids = [lob.split(' - ')[0] for lob in request.filters.lineOfBusiness]
            placeholders = ','.join(['%s'] * len(lob_ids))
            where_conditions.append(f"LineofBusinessId IN ({placeholders})")
            params.extend(lob_ids)
        
        if request.filters.commitmentSizeGroup:
            placeholders = ','.join(['%s'] * len(request.filters.commitmentSizeGroup))
            where_conditions.append(f"CommitmentSizeGroup IN ({placeholders})")
            params.extend(request.filters.commitmentSizeGroup)
        
        if request.filters.riskGroup:
            placeholders = ','.join(['%s'] * len(request.filters.riskGroup))
            where_conditions.append(f"RiskGroupDesc IN ({placeholders})")
            params.extend(request.filters.riskGroup)
        
        if request.filters.bankId:
            placeholders = ','.join(['%s'] * len(request.filters.bankId))
            where_conditions.append(f"BankID IN ({placeholders})")
            params.extend(request.filters.bankId)
        
        if request.filters.region:
            placeholders = ','.join(['%s'] * len(request.filters.region))
            where_conditions.append(f"Region IN ({placeholders})")
            params.extend(request.filters.region)
        
        if request.filters.naicsGrpName:
            placeholders = ','.join(['%s'] * len(request.filters.naicsGrpName))
            where_conditions.append(f"NAICSGrpName IN ({placeholders})")
            params.extend(request.filters.naicsGrpName)
        
        # Handle custom commitment ranges
        if request.filters.customCommitmentRanges:
            range_conditions = []
            for range_filter in request.filters.customCommitmentRanges:
                range_conditions.append("(CommitmentAmt >= %s AND CommitmentAmt <= %s)")
                params.extend([range_filter['min'], range_filter['max']])
            
            if range_conditions:
                where_conditions.append(f"({' OR '.join(range_conditions)})")
        
        # Build the main query
        base_query = """
        SELECT 
            ProcessingDateKey,
            CommitmentAmt,
            OutstandingAmt,
            Region,
            NAICSGrpName,
            CommitmentSizeGroup,
            RiskGroupDesc,
            LineofBusinessId,
            LineofBusiness,
            BankID,
            MaturityTermMonths,
            SpreadBPS,
            YieldPct
        FROM analytics_data
        """
        
        if where_conditions:
            base_query += f" WHERE {' AND '.join(where_conditions)}"
        
        base_query += " ORDER BY ProcessingDateKey DESC, CommitmentAmt DESC"
        
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
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")

@app.get("/api/analytics-data")
def get_analytics_data(limit: Optional[int] = None):
    """Get aggregated analytics data (time series)"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cursor = conn.cursor()
        
        query = "SELECT * FROM aggregated_analytics ORDER BY ProcessingDateKey"
        
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
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")

@app.post("/api/test-analysis")
def test_analysis():
    """Test endpoint for debugging"""
    try:
        import sys
        sys.path.append('/Users/aetingu/Volume Composites')
        from main import testCappedvsUncapped
        return {"status": "success", "message": "Functions imported successfully"}
    except Exception as e:
        import traceback
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}

@app.post("/api/execute-capped-analysis")
def execute_capped_analysis(request: QueryRequest):
    """Execute the testCappedvsUncapped analysis with filtered data"""
    conn = None
    try:
        import pandas as pd
        import sys
        sys.path.append('/Users/aetingu/Volume Composites')
        from main import testCappedvsUncapped, setup_groups
        print(f"Successfully imported analysis functions")
        
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        # Build WHERE conditions based on filters
        where_conditions = []
        params = []
        
        # Handle SBA classification filter (LineofBusinessId = '12' for SBA, != '12' for Non-SBA)
        if request.filters.sbaClassification:
            sba_conditions = []
            for classification in request.filters.sbaClassification:
                if classification.lower() == 'sba':
                    sba_conditions.append("lineofbusinessid = '12'")
                elif classification.lower() == 'non-sba':
                    sba_conditions.append("lineofbusinessid != '12'")
            if sba_conditions:
                where_conditions.append(f"({' OR '.join(sba_conditions)})")
        
        if request.filters.lineOfBusiness:
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
        
    except Exception as e:
        import traceback
        print(f"Error in capped analysis: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")

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
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")

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
