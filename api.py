from typing import Optional, List, Dict, Any
import json
import os
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import polars as pl

from main import (
    get_all_filter_options,
    get_data_optimized,
    setup_groups,
    testCappedvsUncapped,
)
from data_processor import load_and_process_csv


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
        print(f"Attempting to get data from PostgreSQL database with filters: region={req.region}, sba_filter={req.sba_filter}")
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
                csv_df['ProcessingDateKey'] = pd.to_datetime(csv_df['ProcessingDateKey']).dt.strftime('%Y%m%d').astype(int)
            
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
                (df_sorted['CommitmentAmt'][i] - df_sorted['CommitmentAmt'][i-1]) / df_sorted['CommitmentAmt'][i-1]
                if df_sorted['CommitmentAmt'][i-1] != 0 else 0.0
                for i in range(1, len(df_sorted))
            ])
            
            oa_perc_diff = pl.Series([0.0] + [
                (df_sorted['OutstandingAmt'][i] - df_sorted['OutstandingAmt'][i-1]) / df_sorted['OutstandingAmt'][i-1]
                if df_sorted['OutstandingAmt'][i-1] != 0 else 0.0
                for i in range(1, len(df_sorted))
            ])
            
            deals_perc_diff = pl.Series([0.0] + [
                (df_sorted['Deals'][i] - df_sorted['Deals'][i-1]) / df_sorted['Deals'][i-1]
                if df_sorted['Deals'][i-1] != 0 else 0.0
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

