from typing import Optional, List, Dict, Any
import json
import os
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime


import polars as pl

from main import (
    get_all_filter_options,
    get_data_optimized,
    setup_groups,
    testCappedvsUncapped,
    get_max_processing_date,
    get_available_regions,
    read_sql_polars
)
from data_processor import load_and_process_csv
import pandas as pd



class DataRequest(BaseModel):
    selected_columns: Optional[List[str]] = None
    region: str = "Rocky Mountain"
    sba_filter: str = "Non-SBA"  # 'All', 'SBA', 'Non-SBA'
    line_of_business_ids: Optional[List[str]] = None
    commitment_size_groups: Optional[List[str]] = None
    risk_group_descriptions: Optional[List[str]] = None
    row_limit: Optional[int] = 1000
    use_polars: bool = True


class CappedAnalysisRequest(BaseModel):
    selected_columns: Optional[List[str]] = None
    region: str = "Rocky Mountain"
    sba_filter: str = "Non-SBA"
    line_of_business_ids: Optional[List[str]] = None
    commitment_size_groups: Optional[List[str]] = None
    risk_group_descriptions: Optional[List[str]] = None
    cap_value: float = 0.1  # 10% cap value
    output_file: Optional[str] = None
    use_polars: bool = True


app = FastAPI(title="Composites API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load processed data as fallback
try:
    if os.path.exists('processed_data.json'):
        with open('processed_data.json', 'r', encoding='utf-8') as f:
            PROCESSED_DATA = json.load(f)
        print(f"Loaded CSV fallback data: {PROCESSED_DATA['summary']}")
    else:
        print("processed_data.json not found, generating from CSV...")
        PROCESSED_DATA = load_and_process_csv()
        with open('processed_data.json', 'w', encoding='utf-8') as f:
            json.dump(PROCESSED_DATA, f, indent=2, default=str)
except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
    print(f"Error loading CSV fallback data: {e}")
    PROCESSED_DATA = {"filter_options": {}, "analytics_data": [], "raw_data": [], "summary": {}}

# Test database connection on startup
try:
    from main import test_db_connection

    db_status = test_db_connection()
    print(f"Database connection status: {db_status}")
except (ImportError, RuntimeError, OSError) as e:
    print(f"Database connection test failed: {e}")
    print("Will use CSV data as fallback")

class FilterRequest(BaseModel):
    """Request model for filtered queries"""
    filters: Dict[str, List[str]]
    customCommitmentRanges: Optional[List[Dict[str, Any]]] = []
    row_limit: Optional[int] = 10000

class QueryResponse(BaseModel):
    """Response model for query results"""
    status: str
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None



@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/db/status")
def database_status() -> Dict[str, Any]:
    """Check database connection status"""
    try:
        from main import test_db_connection
        status = test_db_connection()
        return status
    except (ImportError, RuntimeError, OSError) as e:
        return {"status": "failed", "error": str(e)}


@app.get("/db/config")
def database_config() -> Dict[str, Any]:
    """Check database configuration"""
    try:
        config = {
            "host": os.getenv('DB_HOST', 'not_set'),
            "port": os.getenv('DB_PORT', 'not_set'),
            "database": os.getenv('DB_NAME', 'not_set'),
            "user": os.getenv('DB_USER', 'not_set'),
            "password_set": bool(os.getenv('DB_PASSWORD')),
            "dotenv_loaded": os.path.exists('.env')
        }
        return config
    except (OSError, KeyError) as e:
        return {"error": str(e)}


@app.get("/filters")
def filters(use_polars: bool = True) -> Dict[str, Any]:
    """Get filter options from PostgreSQL database with CSV fallback"""
    try:
        print("Attempting to get filters from PostgreSQL database...")
        result = get_all_filter_options(use_polars)
        print(f"Successfully loaded filters from database: {len(result)} filter categories")
        return result
    except (RuntimeError, OSError, ConnectionError) as e:
        print(f"Database filters failed, using CSV fallback: {e}")
        fallback_data = PROCESSED_DATA.get("filter_options", {})
        print(f"Using CSV fallback with {len(fallback_data)} filter categories")
        return fallback_data


@app.post("/data")
def data(req: DataRequest) -> Dict[str, Any]:
    """Get data from PostgreSQL database with CSV fallback"""
    try:
        print(
            f"Attempting to get data from PostgreSQL database with filters: region={req.region}, sba_filter={req.sba_filter}")
        df = get_data_optimized(
            selected_columns=req.selected_columns,
            use_polars=req.use_polars,
            show_timing=False,
            row_limit=req.row_limit,
            region=req.region,
            sba_filter=req.sba_filter,
            line_of_business_ids=req.line_of_business_ids,
            commitment_size_groups=req.commitment_size_groups,
            risk_group_descriptions=req.risk_group_descriptions,
        )

        if df is None:
            print("Database returned None, using CSV fallback")
            analytics_data = PROCESSED_DATA.get("analytics_data", [])
            limited_data = analytics_data[:req.row_limit] if req.row_limit else analytics_data
            return {
                "rows": limited_data,
                "columns": req.selected_columns or list(limited_data[0].keys()) if limited_data else [],
                "source": "csv_fallback"
            }

        if hasattr(df, "to_dicts"):
            result = {"rows": df.to_dicts(), "columns": list(df.columns), "source": "database"}
            print(f"Successfully returned {len(result['rows'])} rows from PostgreSQL database")
            return result
        else:
            result = {"rows": df.to_dict(orient="records"), "columns": list(df.columns), "source": "database"}
            print(f"Successfully returned {len(result['rows'])} rows from PostgreSQL database (pandas)")
            return result

    except Exception as e:
        print(f"Database data failed, using CSV fallback: {e}")
        analytics_data = PROCESSED_DATA.get("analytics_data", [])
        limited_data = analytics_data[:req.row_limit] if req.row_limit else analytics_data
        return {
            "rows": limited_data,
            "columns": req.selected_columns or list(limited_data[0].keys()) if limited_data else [],
            "source": "csv_fallback",
            "error": str(e)
        }


@app.post("/composites")
def composites(req: DataRequest) -> Dict[str, Any]:
    """Get composite analysis from PostgreSQL database with CSV fallback"""
    try:
        print(f"Attempting to get composites from PostgreSQL database with filters: region={req.region}")
        df = get_data_optimized(
            selected_columns=req.selected_columns,
            use_polars=True,
            show_timing=False,
            row_limit=req.row_limit,
            region=req.region,
            sba_filter=req.sba_filter,
            line_of_business_ids=req.line_of_business_ids,
            commitment_size_groups=req.commitment_size_groups,
            risk_group_descriptions=req.risk_group_descriptions,
        )

        if df is None or not hasattr(df, 'select'):
            print("Database returned None or invalid DataFrame, using CSV fallback")
            analytics_data = PROCESSED_DATA.get("analytics_data", [])
            series = []
            for item in analytics_data:
                series.append({
                    "ProcessingDateKey": item["ProcessingDateKey"],
                    "ca": item["CommitmentAmt"],
                    "oa": item["OutstandingAmt"],
                    "deals": item["Deals"]
                })
            return {"series": series, "source": "csv_fallback"}

        # Build grouped and capped composites using your main.py logic
        print("Building composites from database data...")
        ca_pivot, oa_pivot, deals_pivot = setup_groups(df)
        result = pl.DataFrame({
            "ProcessingDateKey": ca_pivot["ProcessingDateKey"],
            "ca": ca_pivot["perc_diff"],
            "oa": oa_pivot["perc_diff"],
            "deals": deals_pivot["perc_diff"],
        })

        composites_result = {"series": result.to_dicts(), "source": "database"}
        print(f"Successfully returned {len(composites_result['series'])} composite records from PostgreSQL")
        return composites_result

    except Exception as e:
        print(f"Database composites failed, using CSV fallback: {e}")
        analytics_data = PROCESSED_DATA.get("analytics_data", [])
        series = []
        for item in analytics_data:
            series.append({
                "ProcessingDateKey": item["ProcessingDateKey"],
                "ca": item["CommitmentAmt"],
                "oa": item["OutstandingAmt"],
                "deals": item["Deals"]
            })
        return {"series": series, "source": "csv_fallback", "error": str(e)}


@app.post("/analysis/capped-vs-uncapped")
def capped_vs_uncapped_analysis(req: CappedAnalysisRequest) -> Dict[str, Any]:
    """Run capped vs uncapped analysis using testCappedvsUncapped function"""
    try:
        print(f"Running capped vs uncapped analysis with cap_value={req.cap_value}")

        # Get the base data first
        df = get_data_optimized(
            selected_columns=req.selected_columns,
            use_polars=True,
            show_timing=False,
            row_limit=1000,  # Use a reasonable default for analysis
            region=req.region,
            sba_filter=req.sba_filter,
            line_of_business_ids=req.line_of_business_ids,
            commitment_size_groups=req.commitment_size_groups,
            risk_group_descriptions=req.risk_group_descriptions,
        )

        if df is None or not hasattr(df, 'select'):
            print("Database failed, using CSV data for capped analysis")
            # Use CSV data as fallback
            analytics_data = PROCESSED_DATA.get("analytics_data", [])
            if not analytics_data:
                return {"error": "No data available for capped analysis", "source": "no_data"}

            # Convert CSV data to format needed for testCappedvsUncapped
            import pandas as pd
            csv_df = pd.DataFrame(analytics_data)

            # Convert date strings to integers (YYYYMMDD format)
            if 'ProcessingDateKey' in csv_df.columns:
                csv_df['ProcessingDateKey'] = pd.to_datetime(csv_df['ProcessingDateKey']).dt.strftime('%Y%m%d').astype(
                    int)

            df = pl.from_pandas(csv_df)
            print(f"Using CSV fallback data with {len(df)} records, converted dates to integer format")

        print(f"Available columns: {df.columns}")

        # For CSV data, use the existing calculated differences
        if 'ca_diff' in df.columns and 'oa_diff' in df.columns and 'deals_diff' in df.columns:
            print("Using existing calculated differences from CSV data")
            ca_perc_diff = df['ca_diff'].fill_null(0.0)
            oa_perc_diff = df['oa_diff'].fill_null(0.0)
            deals_perc_diff = df['deals_diff'].fill_null(0.0)
        else:
            print("Calculating percentage differences from available data")
            # Calculate simple period-over-period changes
            df_sorted = df.sort('ProcessingDateKey')

            ca_perc_diff = pl.Series([0.0] + [
                (df_sorted['CommitmentAmt'][i] - df_sorted['CommitmentAmt'][i - 1]) / df_sorted['CommitmentAmt'][i - 1]
                if df_sorted['CommitmentAmt'][i - 1] != 0 else 0.0
                for i in range(1, len(df_sorted))
            ])

            oa_perc_diff = pl.Series([0.0] + [
                (df_sorted['OutstandingAmt'][i] - df_sorted['OutstandingAmt'][i - 1]) / df_sorted['OutstandingAmt'][
                    i - 1]
                if df_sorted['OutstandingAmt'][i - 1] != 0 else 0.0
                for i in range(1, len(df_sorted))
            ])

            deals_perc_diff = pl.Series([0.0] + [
                (df_sorted['Deals'][i] - df_sorted['Deals'][i - 1]) / df_sorted['Deals'][i - 1]
                if df_sorted['Deals'][i - 1] != 0 else 0.0
                for i in range(1, len(df_sorted))
            ])

        # Run the capped vs uncapped analysis
        output_file = req.output_file or f"capped_analysis_{int(time.time())}.csv"
        print(f"Running testCappedvsUncapped with {len(df)} input records...")

        result_df = testCappedvsUncapped(
            cla_input_df=df,
            ca_perc_diff=ca_perc_diff,
            oa_perc_diff=oa_perc_diff,
            deals_perc_diff=deals_perc_diff,
            file_name=output_file
        )

        # Convert result to JSON format
        if hasattr(result_df, 'to_dicts'):
            analysis_results = result_df.to_dicts()
        else:
            analysis_results = result_df.to_dict('records')

        return {
            "analysis_results": analysis_results,
            "output_file": output_file,
            "parameters": {
                "cap_value": req.cap_value,
                "region": req.region,
                "sba_filter": req.sba_filter,
                "filters_applied": {
                    "line_of_business": req.line_of_business_ids,
                    "commitment_size_groups": req.commitment_size_groups,
                    "risk_groups": req.risk_group_descriptions
                }
            },
            "source": "database",
            "record_count": len(analysis_results)
        }

    except (RuntimeError, OSError, ConnectionError, ValueError, KeyError) as e:
        print(f"Capped vs uncapped analysis failed: {e}")
        return {"error": str(e), "source": "analysis_failed"}


# CSV-specific endpoints for dashboard
@app.get("/csv/filters")
def csv_filters() -> Dict[str, Any]:
    """Get filter options from CSV data"""
    return PROCESSED_DATA.get("filter_options", {})


@app.post("/csv/data")
def csv_data(req: DataRequest) -> Dict[str, Any]:
    """Get analytics data from CSV"""
    analytics_data = PROCESSED_DATA.get("analytics_data", [])
    limited_data = analytics_data[:req.row_limit] if req.row_limit else analytics_data
    return {
        "rows": limited_data,
        "columns": req.selected_columns or list(limited_data[0].keys()) if limited_data else [],
        "summary": PROCESSED_DATA.get("summary", {})
    }


@app.post("/csv/composites")
def csv_composites(req: DataRequest) -> Dict[str, Any]:
    """Get composite analysis from CSV data"""
    analytics_data = PROCESSED_DATA.get("analytics_data", [])
    series = []
    for item in analytics_data:
        series.append({
            "ProcessingDateKey": item["ProcessingDateKey"],
            "ca": item["CommitmentAmt"],
            "oa": item["OutstandingAmt"],
            "deals": item["Deals"]
        })
    limited_series = series[:req.row_limit] if req.row_limit else series
    return {
        "series": limited_series,
        "metadata": PROCESSED_DATA.get("summary", {})
    }


@app.get("/db/maxdate")
def get_max_date() -> Dict[str, Any]:
    """Get the latest processing date from the database"""
    try:
        from main import get_db_connection
        conn = get_db_connection()

        if not conn:
            return {"status": "failed", "error": "Unable to connect to database"}

        cursor = conn.cursor()
        cursor.execute('SELECT MAX("ProcessingDateKey") FROM cla_uat.mv_t_cla_input_full_upd')
        max_date = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "max_date": max_date
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@app.get("/db/months-available")
def get_months_available() -> Dict[str, Any]:
    """Get the count of distinct months available in the database"""
    try:
        from main import get_db_connection
        conn = get_db_connection()

        if not conn:
            return {"status": "failed", "error": "Unable to connect to database"}

        cursor = conn.cursor()
        # Count distinct year-month combinations
        cursor.execute('''
            SELECT COUNT(DISTINCT "ProcessingDateKey") as months_available
            FROM cla_uat.mv_t_cla_input_full_upd
        ''')
        months_count = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "months_available": months_count
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@app.get("/db/latest-month-stats")
def get_latest_month_stats() -> Dict[str, Any]:
    """Get record count and total commitment for the latest month"""
    try:
        from main import get_db_connection
        conn = get_db_connection()

        if not conn:
            return {"status": "failed", "error": "Unable to connect to database"}

        cursor = conn.cursor()

        # Get stats for the latest month
        cursor.execute('''
            WITH latest_month AS (
                SELECT MAX("ProcessingDateKey") as max_date
                FROM cla_uat.mv_t_cla_input_full_upd
            )
            SELECT 
                COUNT(*) as record_count,
                SUM("CommitmentAmt") as total_commitment
            FROM cla_uat.mv_t_cla_input_full_upd
            WHERE "ProcessingDateKey" = 
                  (SELECT max_date FROM latest_month)
        ''')

        result = cursor.fetchone()
        record_count = result[0] if result[0] else 0
        total_commitment = result[1] if result[1] else 0

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "record_count": record_count,
            "total_commitment": total_commitment
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@app.get("/db/filter-options")
async def get_filter_options():
    """Get all available filter options for the UI - Database only"""
    try:
        print("=== FILTER OPTIONS REQUEST RECEIVED ===")
        print("Fetching filter options from database...")

        # Check if we have a database connection first
        from main import get_db_connection
        conn = get_db_connection()
        if not conn:
            print("ERROR: Database connection not available")
            return {
                "status": "error",
                "error": "Database connection not available"
            }
        print("Database connection OK")
        conn.close()  # Close it since get_all_filter_options handles its own connection

        # Import and use your existing function from main.py
        from main import get_all_filter_options
        print("Calling get_all_filter_options...")
        filter_options = get_all_filter_options(use_polars=True)

        if not filter_options:
            print("ERROR: No filter options returned from database")
            return {
                "status": "error",
                "error": "No filter options returned from database"
            }

        print(f"Successfully loaded {len(filter_options)} filter categories from database")
        print("Filter categories found:")
        for key, values in filter_options.items():
            print(f"  {key}: {len(values)} options")

        # Format the response
        formatted_options = {
            "lineOfBusiness": filter_options.get('line_of_business_ids', []),
            "commitmentSizeGroup": filter_options.get('commitment_size_groups', []),
            "riskGroup": filter_options.get('risk_group_descriptions', []),
            "bankId": [],  # Add this if you have bank IDs in your database
            "region": filter_options.get('regions', []),
            "naicsGrpName": filter_options.get('sba_classifications', [])  # Map SBA to NAICS
        }

        print("=== FORMATTED OPTIONS FOR UI ===")
        for key, values in formatted_options.items():
            print(f"  {key}: {len(values)} options")
            if len(values) > 0:
                print(f"    Sample: {values[:3]}...")  # Show first 3 items

        return {
            "status": "success",
            "source": "database",
            "options": formatted_options
        }

    except Exception as e:
        print(f"ERROR in get_filter_options: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e)
        }



@app.post("/db/query")
async def execute_filtered_query(request: FilterRequest):
    """Execute a filtered query against the database"""
    start_time = time.time()

    try:
        # Check if we have a database connection
        from main import get_db_connection
        conn = get_db_connection()
        if not conn:
            return QueryResponse(
                status="error",
                error="Database connection not available"
            )

        # Build the SQL query with filters
        where_conditions = []
        params = {}
        param_counter = 1

        # Build WHERE conditions for each filter type
        if request.filters.get('lineOfBusiness'):
            placeholders = []
            for lob in request.filters['lineOfBusiness']:
                param_name = f"lob_{param_counter}"
                params[param_name] = lob
                placeholders.append(f":{param_name}")
                param_counter += 1
            where_conditions.append(f"LineOfBusinessID IN ({','.join(placeholders)})")

        if request.filters.get('commitmentSizeGroup'):
            placeholders = []
            for csg in request.filters['commitmentSizeGroup']:
                param_name = f"csg_{param_counter}"
                params[param_name] = csg
                placeholders.append(f":{param_name}")
                param_counter += 1
            where_conditions.append(f"CommitmentSizeGroup IN ({','.join(placeholders)})")

        if request.filters.get('riskGroup'):
            placeholders = []
            for rg in request.filters['riskGroup']:
                param_name = f"rg_{param_counter}"
                params[param_name] = rg
                placeholders.append(f":{param_name}")
                param_counter += 1
            where_conditions.append(f"RiskGroupDescription IN ({','.join(placeholders)})")

        if request.filters.get('region'):
            placeholders = []
            for region in request.filters['region']:
                param_name = f"region_{param_counter}"
                params[param_name] = region
                placeholders.append(f":{param_name}")
                param_counter += 1
            where_conditions.append(f"Region IN ({','.join(placeholders)})")

        # Handle custom commitment ranges
        if request.customCommitmentRanges:
            range_conditions = []
            for i, range_obj in enumerate(request.customCommitmentRanges):
                min_param = f"range_min_{i}"
                max_param = f"range_max_{i}"
                params[min_param] = range_obj['min']
                params[max_param] = range_obj['max']
                range_conditions.append(f"(CommitmentAmt >= :{min_param} AND CommitmentAmt <= :{max_param})")

            if range_conditions:
                where_conditions.append(f"({' OR '.join(range_conditions)})")

        # Build the main query
        base_query = """
        SELECT 
            ProcessingDateKey,
            LineOfBusinessID,
            CommitmentSizeGroup,
            RiskGroupDescription,
            Region,
            COUNT(*) as RecordCount,
            SUM(CommitmentAmt) as TotalCommitment,
            AVG(CommitmentAmt) as AvgCommitment,
            MIN(CommitmentAmt) as MinCommitment,
            MAX(CommitmentAmt) as MaxCommitment
        FROM cla_volume_composites
        """

        if where_conditions:
            base_query += f" WHERE {' AND '.join(where_conditions)}"

        base_query += """
        GROUP BY ProcessingDateKey, LineOfBusinessID, CommitmentSizeGroup, RiskGroupDescription, Region
        ORDER BY ProcessingDateKey DESC, TotalCommitment DESC
        """

        if request.row_limit:
            base_query += f" LIMIT {request.row_limit}"

        # Execute query using polars for better performance
        try:
            df = read_sql_polars(conn, base_query, params if params else None)
            results = df.to_dicts()
        except:
            # Fallback to pandas if polars fails
            df = pd.read_sql(base_query, conn, params=params if params else None)
            results = df.to_dict('records')

        # Calculate summary statistics
        total_records = len(results)
        total_commitment = sum(row.get('TotalCommitment', 0) for row in results if row.get('TotalCommitment'))

        conn.close()
        execution_time = round((time.time() - start_time) * 1000, 2)

        return QueryResponse(
            status="success",
            results={
                "rows": results,
                "totalRecords": total_records,
                "totalCommitment": total_commitment,
                "executionTime": execution_time,
                "query": {
                    "filters": request.filters,
                    "customRanges": request.customCommitmentRanges,
                    "timestamp": datetime.now().isoformat()
                }
            },
            execution_time=execution_time
        )

    except Exception as e:
        execution_time = round((time.time() - start_time) * 1000, 2)
        print(f"Error executing query: {str(e)}")
        return QueryResponse(
            status="error",
            error=str(e),
            execution_time=execution_time
        )
