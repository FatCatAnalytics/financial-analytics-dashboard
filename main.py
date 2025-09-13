import polars as pl
import pandas as pd
import os
import socket
from importlib import import_module

try:
    load_dotenv = import_module("dotenv").load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> None:
        return None
import time
from typing import Optional, Union, Dict, Any, List
import numpy as np
from urllib.parse import quote_plus

# Load environment variables
load_dotenv()


class BusinessConfig:
    """Configuration class for business logic constants."""
    MAX_BANK_CELL_WEIGHT = 0.5
    MAX_MOM = 0.1
    MAX_MOM_HIGH = 0.2
    MIN_MOM = -MAX_MOM / (1 + MAX_MOM)
    MIN_MOM_HIGH = -MAX_MOM_HIGH / (1 + MAX_MOM_HIGH)
    HIGH_BREACH_PERC = 0.5
    RESIDUAL_LIMIT = 1000


def validate_env_variables() -> bool:
    """Validate that all required environment variables are set."""
    required_vars = ['DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT', 'DB_NAME']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    return True


def test_network_connectivity() -> bool:
    """Test if we can reach the database server"""
    if not validate_env_variables():
        return False

    host = os.getenv('DB_HOST')
    port = int(os.getenv('DB_PORT'))

    print(f"Testing connection to {host}:{port}")

    try:
        # Test socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)  # 10 second timeout
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            print("✓ Network connection successful")
            return True
        else:
            print("✗ Network connection failed")
            return False

    except OSError as e:
        print(f"✗ Network test error: {e}")
        return False


def get_db_connection() -> Optional[Any]:
    """Create and return a database connection with optimized settings."""
    if not validate_env_variables():
        return None

    try:
        # Import locally to avoid hard dependency at module import time
        try:
            psycopg2_mod = import_module("psycopg2")  # type: ignore[attr-defined]
        except ModuleNotFoundError:
            print("psycopg2 is not installed. Install it to enable DB connections.")
            return None
        conn = psycopg2_mod.connect(
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT')),
            database=os.getenv('DB_NAME'),
            sslmode='require',
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
            application_name='large_data_transfer'
        )
        conn.set_session(readonly=True)
        return conn
    except RuntimeError as e:
        print(f"Connection error: {e}")
        return None


def get_db_connection_uri() -> Optional[str]:
    """Get database connection URI for SQLAlchemy and Polars"""
    try:
        load_dotenv()

        host = os.getenv('DB_HOST')
        database = os.getenv('DB_NAME')
        user = os.getenv('DB_USER')
        password = os.getenv('DB_PASSWORD')
        port = os.getenv('DB_PORT', '5432')

        if not all([host, database, user, password]):
            missing = [k for k, v in {'host': host, 'database': database, 'user': user, 'password': password}.items() if
                       not v]
            print(f"Missing required environment variables: {missing}")
            return None

        # Clean the password by removing quotes if they exist
        if password.startswith("'") and password.endswith("'"):
            password = password[1:-1]
        elif password.startswith('"') and password.endswith('"'):
            password = password[1:-1]

        # URL encode the password to handle special characters
        from urllib.parse import quote_plus
        encoded_password = quote_plus(password)

        # Construct the PostgreSQL URI
        connection_uri = f"postgresql://{user}:{encoded_password}@{host}:{port}/{database}"
        print(f"Database URI constructed: postgresql://{user}:***@{host}:{port}/{database}")

        return connection_uri

    except Exception as e:
        print(f"Error creating database URI: {e}")
        return None


def test_db_connection() -> Dict[str, Any]:
    """Test database connection and return connection status with max date"""
    try:
        conn = get_db_connection()
        if not conn:
            return {
                "status": "failed",
                "error": "Could not establish connection",
                "max_date": None
            }

        # Get the database version
        with conn.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]

            # Get the max processing date
            cursor.execute('SELECT MAX("ProcessingDateKey") FROM cla_uat.mv_t_cla_input_full_upd')  # Replace with actual table name
            max_date = cursor.fetchone()[0]

        conn.close()

        return {
            "status": "connected",
            "version": version,
            "max_date": max_date
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "max_date": None
        }


def read_sql_polars(query: str) -> Optional[pl.DataFrame]:
    """Read SQL query using Polars with proper connection handling"""
    try:
        print(f"Executing query with Polars: {query[:100]}...")

        # Get the connection URI instead of a connection object
        connection_uri = get_db_connection_uri()
        if not connection_uri:
            print("No database connection URI available")
            return None

        # Use Polars read_database_uri method
        df = pl.read_database_uri(
            query=query,
            uri=connection_uri
        )
        print(f"Polars query successful, returned {len(df)} rows")
        return df

    except Exception as e:
        print(f"Polars read_database_uri failed: {e}")

        # Fallback to pandas with SQLAlchemy engine
        try:
            print("Falling back to pandas with SQLAlchemy...")
            from sqlalchemy import create_engine

            connection_uri = get_db_connection_uri()
            if not connection_uri:
                return None

            engine = create_engine(connection_uri)

            # Use pandas with SQLAlchemy engine
            df_pandas = pd.read_sql(query, engine)

            # Convert pandas DataFrame to Polars DataFrame
            df_polars = pl.from_pandas(df_pandas)
            print(f"Pandas fallback successful, returned {len(df_polars)} rows")

            engine.dispose()
            return df_polars

        except Exception as pandas_error:
            print(f"Pandas fallback also failed: {pandas_error}")
            return None


def get_available_sba_classifications() -> List[str]:
    """Get SBA classification options (simpler since these are fixed)"""
    return ['All', 'SBA', 'Non-SBA']


def get_max_processing_date() -> Optional[str]:
    """Get the maximum ProcessingDateKey from the database."""
    try:
        conn = get_db_connection()
        if not conn:
            return None

        with conn.cursor() as cursor:
            # Replace 'your_table' with the actual table name containing ProcessingDateKey
            cursor.execute('SELECT MAX("ProcessingDateKey") FROM cla_uat.mv_t_cla_input_full_upd')
            max_date = cursor.fetchone()[0]

        conn.close()
        return max_date
    except Exception as e:
        print(f"Error getting max processing date: {e}")
        return None


def get_available_line_of_business_ids(use_polars: bool = True) -> List[Dict[str, str]]:
    """Get a list of all available Line of Business IDs with their descriptions from the database"""
    try:
        # First test network connectivity
        if not test_network_connectivity():
            print("Cannot reach database server. Check network access/VPN.")
            return []

        # Query to get LineofBusinessId with potential business names/descriptions
        # You may need to join with another table to get business names if available
        query = """
        SELECT DISTINCT "LineofBusinessId",
               COUNT(*) as record_count
        FROM cla_uat.mv_t_cla_input_full_upd 
        WHERE "LineofBusinessId" IS NOT NULL 
        AND "LineofBusinessId" != 'NULL'
        AND "LineofBusinessId" != ''
        GROUP BY "LineofBusinessId"
        ORDER BY "LineofBusinessId"
        """

        print("Fetching available Line of Business IDs...")

        if use_polars:
            df = read_sql_polars(query)
            if df is None:
                return []
            lob_options = []
            for row in df.to_dicts():
                lob_id = row['LineofBusinessId']
                count = row['record_count']
                # Add SBA indicator for reference
                sba_indicator = " (SBA)" if lob_id == '12' else " (Non-SBA)"
                lob_options.append({
                    'id': lob_id,
                    'display_name': f"LOB {lob_id}{sba_indicator}",
                    'record_count': count
                })
        else:
            # Get a database connection
            conn = get_db_connection()
            if conn is None:
                return []
            df = pd.read_sql_query(query, conn)
            lob_options = []
            for _, row in df.iterrows():
                lob_id = row['LineofBusinessId']
                count = row['record_count']
                # Add SBA indicator for reference
                sba_indicator = " (SBA)" if lob_id == '12' else " (Non-SBA)"
                lob_options.append({
                    'id': lob_id,
                    'display_name': f"LOB {lob_id}{sba_indicator}",
                    'record_count': count
                })
            # Close the connection
            conn.close()

        print(f"Found {len(lob_options)} Line of Business IDs:")
        for lob_item in lob_options:
            print(f"  - {lob_item['display_name']} ({lob_item['record_count']:,} records)")

        return lob_options

    except Exception as e:
        print(f"Error fetching Line of Business IDs: {e}")
        return []


def get_available_commitment_size_groups(use_polars: bool = True) -> List[str]:
    """Get a list of all available Commitment Size Groups from the database"""
    try:
        # First test network connectivity
        if not test_network_connectivity():
            print("Cannot reach database server. Check network access/VPN.")
            return []

        query = """
        SELECT DISTINCT "CommitmentSizeGroup" 
        FROM cla_uat.mv_t_cla_input_full_upd 
        WHERE "CommitmentSizeGroup" IS NOT NULL 
        AND "CommitmentSizeGroup" != 'NULL'
        AND "CommitmentSizeGroup" != ''
        ORDER BY "CommitmentSizeGroup"
        """

        print("Fetching available Commitment Size Groups...")

        if use_polars:
            df = read_sql_polars(query)
            if df is None:
                return []
            size_groups = df['CommitmentSizeGroup'].to_list()  # type: ignore[index]
        else:
            # Get a database connection
            conn = get_db_connection()
            if conn is None:
                return []
            df = pd.read_sql_query(query, conn)
            size_groups = df['CommitmentSizeGroup'].tolist()
            # Close the connection
            conn.close()

        # Filter out any None or empty values that might have slipped through
        size_groups = [sg for sg in size_groups if sg and sg.strip() and sg != 'NULL']

        print(f"Found {len(size_groups)} Commitment Size Groups: {size_groups}")
        return size_groups

    except Exception as e:
        print(f"Error fetching Commitment Size Groups: {e}")
        return []


def get_available_risk_group_descriptions(use_polars: bool = True) -> List[str]:
    """Get a list of all available Risk Group Descriptions from the database"""
    try:
        # First test network connectivity
        if not test_network_connectivity():
            print("Cannot reach database server. Check network access/VPN.")
            return []

        query = """
        SELECT DISTINCT "RiskGroupDesc" 
        FROM cla_uat.mv_t_cla_input_full_upd 
        WHERE "RiskGroupDesc" IS NOT NULL 
        AND "RiskGroupDesc" != 'NULL'
        AND "RiskGroupDesc" != ''
        ORDER BY "RiskGroupDesc"
        """

        print("Fetching available Risk Group Descriptions...")

        if use_polars:
            df = read_sql_polars(query)
            if df is None:
                return []
            risk_groups = df['RiskGroupDesc'].to_list()  # type: ignore[index]
        else:
            # Get a database connection
            conn = get_db_connection()
            if conn is None:
                return []
            df = pd.read_sql_query(query, conn)
            risk_groups = df['RiskGroupDesc'].tolist()
            # Close the connection
            conn.close()

        # Filter out any None or empty values that might have slipped through
        risk_groups = [rg for rg in risk_groups if rg and rg.strip() and rg != 'NULL']

        print(f"Found {len(risk_groups)} Risk Group Descriptions: {risk_groups}")
        return risk_groups

    except Exception as e:
        print(f"Error fetching Risk Group Descriptions: {e}")
        return []


def get_all_filter_options(use_polars: bool = True) -> Dict[str, Union[List[str], List[Dict[str, str]]]]:
    """Get all filter options in a single call for efficient dashboard loading"""
    try:
        print("Fetching all filter options...")

        options = {
            'regions': get_available_regions(use_polars),
            'sba_classifications': get_available_sba_classifications(),
            'line_of_business_ids': get_available_line_of_business_ids(use_polars),
            'commitment_size_groups': get_available_commitment_size_groups(use_polars),
            'risk_group_descriptions': get_available_risk_group_descriptions(use_polars)
        }

        print("Successfully loaded all filter options:")
        for key, values in options.items():
            print(f"  {key}: {len(values)} options")

        return options

    except Exception as e:
        print(f"Error fetching all filter options: {e}")
        return {}


def get_available_regions(use_polars: bool = True) -> List[str]:
    """Get a list of all available regions from the database"""
    try:
        # First test network connectivity
        if not test_network_connectivity():
            print("Cannot reach database server. Check network access/VPN.")
            return []

        query = """
        SELECT DISTINCT "Region" 
        FROM cla_uat.mv_t_cla_input_full_upd 
        WHERE "Region" IS NOT NULL 
        AND "Region" != 'NULL'
        AND "Region" != ''
        ORDER BY "Region"
        """

        print("Fetching available regions...")

        if use_polars:
            df = read_sql_polars(query)
            if df is None:
                return []
            regions = df['Region'].to_list()  # type: ignore[index]
        else:
            # Get a database connection
            conn = get_db_connection()
            if conn is None:
                return []
            df = pd.read_sql_query(query, conn)
            regions = df['Region'].tolist()
            # Close the connection
            conn.close()

        # Filter out any None or empty values that might have slipped through
        regions = [r for r in regions if r and r.strip() and r != 'NULL']

        print(f"Found {len(regions)} regions: {regions}")
        return regions

    except Exception as e:
        print(f"Error fetching regions: {e}")
        return []


def get_data_optimized(
        selected_columns: Optional[list] = None,
        use_polars: bool = True,
        show_timing: bool = True,
        row_limit: Optional[int] = None,
        region: str = 'Rocky Mountain',
        sba_filter: str = 'Non-SBA',  # 'All', 'SBA', or 'Non-SBA'
        line_of_business_ids: Optional[Union[str, List[str]]] = None,  # Specific LOB IDs
        commitment_size_groups: Optional[Union[str, List[str]]] = None,
        risk_group_descriptions: Optional[Union[str, List[str]]] = None
) -> Union[pl.DataFrame, pd.DataFrame, None]:
    """
    Optimized version to load region data with flexible filtering options

    Parameters:
    selected_columns (list): List of columns to retrieve (None for all columns)
    use_polars (bool): Whether to use Polars (True) or pandas (False)
    show_timing (bool): Whether to show timing information
    row_limit (Optional[int]): Limit the number of rows returned (None for no limit)
    region (str): Region to filter by (default: 'Rocky Mountain')
    sba_filter (str): SBA classification filter - 'All', 'SBA', or 'Non-SBA' (default: 'Non-SBA')
    line_of_business_ids (Optional[Union[str, List[str]]]): Specific Line of Business ID(s) to filter by
    commitment_size_groups (Optional[Union[str, List[str]]]): Commitment size group(s) to filter by
    risk_group_descriptions (Optional[Union[str, List[str]]]): Risk group description(s) to filter by

    Returns:
    DataFrame: Polars or pandas DataFrame containing the filtered data, or None if error
    """
    start_time = time.time()

    # First test network connectivity
    if not test_network_connectivity():
        print("Cannot reach database server. Check network access/VPN.")
        return None

    # Select specific columns if provided, otherwise use '*'
    if selected_columns:
        columns_str = ", ".join([f'"{col}"' for col in selected_columns])
    else:
        columns_str = "*"

    # Build WHERE conditions
    where_conditions = [
        f"\"Region\" = '{region}'"
    ]

    # Add SBA filter - this is the primary classification filter
    if sba_filter == 'SBA':
        where_conditions.append("\"LineofBusinessId\" = '12'")
        print("Applying SBA classification filter: LineofBusinessId = '12'")
    elif sba_filter == 'Non-SBA':
        where_conditions.append("\"LineofBusinessId\" != '12'")
        print("Applying Non-SBA classification filter: LineofBusinessId != '12'")
    else:
        print("No SBA classification filter applied (All SBA classifications)")

    # Add specific Line of Business ID filter - this is secondary and works within the SBA classification
    if line_of_business_ids is not None:
        if isinstance(line_of_business_ids, list):
            lob_list = [f"'{lob}'" for lob in line_of_business_ids]
            where_conditions.append(f"\"LineofBusinessId\" IN ({', '.join(lob_list)})")
            print("Applying specific Line of Business ID filter:", ", ".join(line_of_business_ids))
        else:
            where_conditions.append(f"\"LineofBusinessId\" = '{line_of_business_ids}'")
            print("Applying specific Line of Business ID filter:", line_of_business_ids)
    else:
        print("No specific Line of Business ID filter applied")

    # Add commitment size group filter
    if commitment_size_groups is not None:
        if isinstance(commitment_size_groups, list):
            csg_list = [f"'{csg}'" for csg in commitment_size_groups]
            where_conditions.append(f"\"CommitmentSizeGroup\" IN ({', '.join(csg_list)})")
            print("Applying Commitment Size Group filter:", ", ".join(commitment_size_groups))
        else:
            where_conditions.append(f"\"CommitmentSizeGroup\" = '{commitment_size_groups}'")
            print("Applying Commitment Size Group filter:", commitment_size_groups)

    # Add risk group description filter
    if risk_group_descriptions is not None:
        if isinstance(risk_group_descriptions, list):
            rgd_list = [f"'{rgd}'" for rgd in risk_group_descriptions]
            where_conditions.append(f"\"RiskGroupDesc\" IN ({', '.join(rgd_list)})")
            print("Applying Risk Group Description filter:", ", ".join(risk_group_descriptions))
        else:
            where_conditions.append(f"\"RiskGroupDesc\" = '{risk_group_descriptions}'")
            print("Applying Risk Group Description filter:", risk_group_descriptions)

    # Add maturity filter to exclude matured loans with low outstanding amounts
    where_conditions.append(
        "NOT (\"CurrentMaturityDateKey\" < \"ProcessingDateKey\" AND NULLIF(\"OutstandingAmt\", 'NULL') :: float8 < 1000)"
    )

    # Build the complete query
    query = f"""
    SELECT {columns_str}
    FROM cla_uat.mv_t_cla_input_full_upd
    WHERE {' AND '.join(where_conditions)}
    """

    # Add LIMIT clause if row_limit is specified
    if row_limit is not None:
        query += f"\nLIMIT {row_limit}"
        print(f"Applying row limit: {row_limit}")

    print("\nApplied Filters Summary:")
    print("- Region:", region)
    print("- SBA Classification:", sba_filter)
    if line_of_business_ids:
        print("- Specific Line of Business IDs:", line_of_business_ids)
    if commitment_size_groups:
        print("- Commitment Size Groups:", commitment_size_groups)
    if risk_group_descriptions:
        print("- Risk Group Descriptions:", risk_group_descriptions)

    print("\nQuery:")
    print(query)

    try:
        print("Network test passed, attempting database connection...")
        query_start = time.time()

        if use_polars:
            print("Using Polars for data processing...")
            df = read_sql_polars(query)
            if df is None:
                return None
        else:
            print("Using pandas for data processing...")
            conn = get_db_connection()
            if conn is None:
                return None
            try:
                # Use chunksize for pandas to process in batches
                chunks = []
                for chunk in pd.read_sql_query(query, conn, chunksize=100000):
                    chunks.append(chunk)
                df = pd.concat(chunks) if chunks else pd.DataFrame()
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

        query_time = time.time() - query_start
        print("✓ Database query and transfer completed in", f"{query_time:.2f}", "seconds")

        if df is None or (isinstance(df, pd.DataFrame) and df.empty) or (isinstance(df, pl.DataFrame) and len(df) == 0):
            print("Warning: Query returned no data")
            return None

        print("Retrieved", f"{len(df) if use_polars else len(df.index):,}", "rows")

        # Verify required columns exist
        required_columns = ["ProcessingDateKey", "BankID", "CommitmentAmt", "OutstandingAmt"]
        if use_polars:
            missing_columns = [col for col in required_columns if col not in df.columns]
        else:
            missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            print("Warning: Missing required columns:", missing_columns)
            return None

        # Add SBA classification based on LineofBusinessId
        if use_polars:
            if "SBA_Classification" not in df.columns:
                process_start = time.time()
                df = df.with_columns(
                    pl.when(pl.col("LineofBusinessId") == "12")
                    .then(pl.lit("SBA"))
                    .otherwise(pl.lit("Non-SBA"))
                    .alias("SBA_Classification")
                )
                process_time = time.time() - process_start
                if show_timing:
                    print("- Post-processing time:", f"{process_time:.2f}", "seconds")
        else:
            if "SBA_Classification" not in df.columns:
                process_start = time.time()
                df['SBA_Classification'] = 'Non-SBA'  # Default
                df.loc[df['LineofBusinessId'] == '12', 'SBA_Classification'] = 'SBA'
                process_time = time.time() - process_start
                if show_timing:
                    print("- Post-processing time:", f"{process_time:.2f}", "seconds")

        if show_timing:
            total_time = time.time() - start_time
            print("\nPerformance Metrics:")
            print("- Database query and transfer time:", f"{query_time:.2f}", "seconds")
            print("- Total execution time:", f"{total_time:.2f}", "seconds")

        return df

    except Exception as e:
        print(f"Error loading data: {e}")
        return None


def aggregate_composites(bank_pivot_df: pl.DataFrame, bankid_mod_list: List[str],
                         bankid_inc_list: List[str]) -> List[float]:
    """Calculate aggregated composites using vectorized Polars operations.

    For each row t, compute:
      prior_sum = sum_banks(mod_{t-1, bank} * inc_{t, bank})
      curr_sum  = sum_banks(mod_{t, bank}   * inc_{t, bank})
      perc_diff = (curr_sum / prior_sum) - 1, guarded against divide-by-zero
    """

    print("aggregate_composites: DataFrame rows:", len(bank_pivot_df))
    print("aggregate_composites: bankid_mod_list items:", len(bankid_mod_list))
    print("aggregate_composites: bankid_inc_list items:", len(bankid_inc_list))

    # Ensure lists align
    if len(bankid_mod_list) != len(bankid_inc_list):
        raise ValueError("bankid_mod_list and bankid_inc_list must have the same length")

    # Build expressions for current and prior weighted components
    curr_components = []
    prior_components = []
    for mod_col, inc_col in zip(bankid_mod_list, bankid_inc_list):
        mod_expr = pl.col(mod_col).cast(pl.Float64).fill_null(0.0)
        inc_expr = pl.col(inc_col).cast(pl.Float64).fill_null(0.0)
        curr_components.append(mod_expr * inc_expr)
        prior_components.append(mod_expr.shift(1) * inc_expr)

    df_tmp = bank_pivot_df.with_columns([
        pl.sum_horizontal(curr_components).alias("_curr_sum"),
        pl.sum_horizontal(prior_components).alias("_prior_sum"),
    ]).with_columns([
        pl.when((pl.col("_prior_sum").is_null()) | (pl.col("_prior_sum") == 0) | (pl.col("_curr_sum").is_null()))
        .then(None)
        .otherwise((pl.col("_curr_sum") / pl.col("_prior_sum")) - 1)
        .alias("_perc_diff")
    ])

    result_list = df_tmp["_perc_diff"].to_list()
    # Ensure first period is NaN explicitly
    if result_list:
        result_list[0] = np.nan
    print("aggregate_composites: Returning values:", len(result_list))
    return result_list


def get_capped_diff_pivoted_revs(group_df: pl.LazyFrame, amt_field: str, max_mom: float, min_mom: float,
                                 max_mom_high: float, min_mom_high: float, high_breach_perc: float) -> pl.DataFrame:
    """Get capped differential pivoted revenues with breach detection."""
    # Force evaluation to DataFrame before pivoting
    group_df = group_df.collect()

    # Ensure BankID is correctly cast to string before pivoting
    group_df = group_df.with_columns(pl.col("BankID").cast(pl.Utf8))

    # Pivot the data on the field
    cla_pivot_df = group_df.pivot(index='ProcessingDateKey', on='BankID', values=amt_field) \
        .sort("ProcessingDateKey")

    # Get a list of the bank IDs from the columns
    bank_id_list = [col for col in cla_pivot_df.columns if col != "ProcessingDateKey"]

    # Process each BankID
    for bank_id in bank_id_list:
        values = cla_pivot_df[bank_id].to_numpy()
        perc_diff_raw = [np.nan]
        include = [False]  # First row is always False since no prior period

        for i in range(1, len(values)):
            prev, curr = values[i - 1], values[i]
            if np.isnan(prev) or np.isnan(curr) or prev == 0:
                perc_diff_raw.append(np.nan)
                include.append(False)  # Don't include if data is invalid
            else:
                perc_diff_raw.append((curr / prev) - 1)
                include.append(True)  # Include if data is valid

        cla_pivot_df = cla_pivot_df.with_columns([
            pl.Series(f"{bank_id}_perc_diff_raw", perc_diff_raw),
            pl.Series(f"{bank_id}_inc", include)
        ])

    perc_diff_cols = [f"{bank_id}_perc_diff_raw" for bank_id in bank_id_list]

    # Make sure all numerical operations use properly typed values
    perc_diff_df = cla_pivot_df.with_columns([
        pl.sum_horizontal([
            (~pl.col(c).is_null()).cast(pl.Int8) for c in perc_diff_cols]).alias("actual_data"),
        pl.sum_horizontal([
            (pl.col(c) > max_mom).cast(pl.Int8) for c in perc_diff_cols]).alias("num_breaches_max"),
        pl.sum_horizontal([
            (pl.col(c) < min_mom).cast(pl.Int8) for c in perc_diff_cols]).alias("num_breaches_min"),
    ]).with_columns([
        pl.when(pl.col("actual_data") == 0)
        .then(0.0)
        .otherwise(pl.col("num_breaches_max") / pl.col("actual_data"))
        .alias("perc_breaches_max"),
        pl.when(pl.col("actual_data") == 0)
        .then(0.0)
        .otherwise(pl.col("num_breaches_min") / pl.col("actual_data"))
        .alias("perc_breaches_min"),
    ]).with_columns([
        (pl.col("perc_breaches_max") >= high_breach_perc).alias("high_lim_max"),
        (pl.col("perc_breaches_min") >= high_breach_perc).alias("high_lim_min"),
    ]).with_columns([
        pl.when(pl.col("high_lim_max")).then(max_mom_high).otherwise(max_mom).alias("lim_max"),
        pl.when(pl.col("high_lim_min")).then(min_mom_high).otherwise(min_mom).alias("lim_min"),
    ])

    cla_pivot_df = cla_pivot_df.hstack(perc_diff_df.select(["lim_max", "lim_min"]))

    # Apply capping logic
    for bank_id in bank_id_list:
        values = cla_pivot_df[bank_id].to_numpy()
        lim_max = cla_pivot_df["lim_max"].to_numpy()
        lim_min = cla_pivot_df["lim_min"].to_numpy()

        perc_diff_capped = [np.nan]
        adjusted = [values[0]]
        include_capped = [False]  # First row inclusion is always False

        for i in range(1, len(values)):
            prev, curr = adjusted[i - 1], values[i]
            if np.isnan(prev) or np.isnan(curr) or prev == 0:
                perc_diff_capped.append(np.nan)
                adjusted.append(curr)
                include_capped.append(False)  # Don't include if invalid data
            else:
                capped = max(min((curr / prev) - 1, lim_max[i]), lim_min[i])
                new_val = prev * (1 + capped)
                perc_diff_capped.append(capped)
                adjusted.append(new_val)
                include_capped.append(True)  # Include if valid data

        cla_pivot_df = cla_pivot_df.with_columns([
            pl.Series(f"{bank_id}_perc_diff", perc_diff_capped),
            pl.Series(f"{bank_id}_mod", adjusted),
            pl.Series(f"{bank_id}_inc", include_capped)  # Update inclusion flags based on capped logic
        ])

    mod_cols = [f"{bank_id}_mod" for bank_id in bank_id_list]
    inc_cols = [f"{bank_id}_inc" for bank_id in bank_id_list]

    # Fixed: Call the corrected aggregate_composites function
    perc_diff_list = aggregate_composites(cla_pivot_df, mod_cols, inc_cols)
    cla_pivot_df = cla_pivot_df.with_columns([
        pl.Series("perc_diff", perc_diff_list)
    ])

    return cla_pivot_df


def cap_max_proportion(group_df: pl.DataFrame, amt_field: str,
                       lim_perc: float = BusinessConfig.MAX_BANK_CELL_WEIGHT) -> pl.DataFrame:
    """Cap the maximum percentage of any bank in any period to a given value."""

    # Calculate sum per period
    sum_col = f"{amt_field}Sum"
    max_col = f"{amt_field}Max"
    perc_col = f"{amt_field}Perc"
    capped_col = f"{amt_field}Capped"

    # Ensure the amount field is numeric
    result_df = group_df.with_columns([
        pl.col(amt_field).cast(pl.Float64)
    ])

    # Add period totals and percentages
    result_df = result_df.with_columns([
        # Calculate sum and percentage for each processing date
        pl.col(amt_field).sum().over("ProcessingDateKey").alias(sum_col),
    ]).with_columns([
        # Calculate percentage
        (pl.col(amt_field) / pl.col(sum_col)).alias(perc_col),
    ]).with_columns([
        # Calculate max percentage per period
        pl.col(perc_col).max().over("ProcessingDateKey").alias(max_col),
    ]).with_columns([
        # Apply capping logic
        pl.when(
            (pl.col(max_col) > lim_perc) & (pl.col(max_col) < 1.0)
        ).then(
            pl.when(pl.col(perc_col) == pl.col(max_col))
            .then(pl.col(sum_col) * lim_perc)
            .otherwise((1 - lim_perc) * pl.col(amt_field) / (1 - pl.col(max_col)))
        ).otherwise(
            pl.col(amt_field)
        ).alias(capped_col)
    ])

    return result_df


def setup_groups(cla_input_df: pl.DataFrame, max_mom: float = BusinessConfig.MAX_MOM,
                 min_mom: float = BusinessConfig.MIN_MOM, max_mom_high: float = BusinessConfig.MAX_MOM_HIGH,
                 min_mom_high: float = BusinessConfig.MIN_MOM_HIGH,
                 high_breach_perc: float = BusinessConfig.HIGH_BREACH_PERC) -> tuple:
    """Set up groups with capping and pivoting logic - complete pandas equivalent."""

    # Check if it's a LazyFrame and collect if needed, otherwise use as is
    if hasattr(cla_input_df, 'collect'):
        cla_input_df = cla_input_df.collect()

    # First check what types we're dealing with and handle accordingly
    print("Initial column types:", cla_input_df.dtypes)

    # Handle NULL strings by converting to proper nulls, being type-aware
    def safe_null_replacement(col_name: str):
        col_dtype = cla_input_df.select(pl.col(col_name)).dtypes[0]
        if col_dtype == pl.Utf8:  # If it's a string column
            return pl.when(pl.col(col_name) == "NULL").then(None).otherwise(pl.col(col_name))
        else:  # If it's already numeric
            return pl.col(col_name)

    # Apply safe null replacement and convert to numeric
    cla_input_df = cla_input_df.with_columns([
        safe_null_replacement('CommitmentAmt').cast(pl.Float64, strict=False).alias('CommitmentAmt'),
        safe_null_replacement('OutstandingAmt').cast(pl.Float64, strict=False).alias('OutstandingAmt'),
        pl.col('ProcessingDateKey').cast(pl.Int64, strict=False),
        pl.col('BankID').cast(pl.Utf8)  # Keep BankID as string
    ])

    # Fill any resulting nulls with zeros
    cla_input_df = cla_input_df.with_columns([
        pl.col('CommitmentAmt').fill_null(0.0),
        pl.col('OutstandingAmt').fill_null(0.0)
    ])

    print("After cleaning column types:", cla_input_df.dtypes)

    # Group by ProcessingDateKey and BankID and aggregate
    cla_group_df = (cla_input_df
    .group_by(['ProcessingDateKey', 'BankID'])
    .agg([
        pl.col('CommitmentAmt').sum().alias('CommitmentAmt'),
        pl.col('CommitmentAmt').len().alias('Deals'),  # Count of records
        pl.col('OutstandingAmt').sum().alias('OutstandingAmt')
    ]))

    # Apply proportion capping for each amount field
    cla_group_df = cap_max_proportion(cla_group_df, 'CommitmentAmt')
    cla_group_df = cap_max_proportion(cla_group_df, 'OutstandingAmt')
    cla_group_df = cap_max_proportion(cla_group_df, 'Deals')

    print("Group DataFrame columns after capping:", cla_group_df.columns)

    # Get pivoted dataframes for each capped field
    cla_ca_pivot_df = get_capped_diff_pivoted_revs(
        cla_group_df.lazy(), 'CommitmentAmtCapped', max_mom, min_mom, max_mom_high, min_mom_high, high_breach_perc
    )

    cla_oa_pivot_df = get_capped_diff_pivoted_revs(
        cla_group_df.lazy(), 'OutstandingAmtCapped', max_mom, min_mom, max_mom_high, min_mom_high, high_breach_perc
    )

    cla_deals_pivot_df = get_capped_diff_pivoted_revs(
        cla_group_df.lazy(), 'DealsCapped', max_mom, min_mom, max_mom_high, min_mom_high, high_breach_perc
    )

    return cla_ca_pivot_df, cla_oa_pivot_df, cla_deals_pivot_df


def testCappedvsUncapped(cla_input_df, ca_perc_diff, oa_perc_diff, deals_perc_diff, file_name):
    start_time = time.time()
    print("Starting data processing...")

    # Debug: Print the lengths and first few values
    print(f"ca_perc_diff length: {len(ca_perc_diff)}")
    print(f"oa_perc_diff length: {len(oa_perc_diff)}")
    print(f"deals_perc_diff length: {len(deals_perc_diff)}")
    if hasattr(ca_perc_diff, 'to_list'):
        print("ca_perc_diff first 5 values:", ca_perc_diff.to_list()[:5])
    else:
        print("ca_perc_diff first 5 values:", list(ca_perc_diff)[:5])
    if hasattr(oa_perc_diff, 'to_list'):
        print("oa_perc_diff first 5 values:", oa_perc_diff.to_list()[:5])
    else:
        print("oa_perc_diff first 5 values:", list(oa_perc_diff)[:5])

    # Convert to Polars DataFrame if not already
    if not isinstance(cla_input_df, pl.DataFrame):
        if hasattr(cla_input_df, 'collect'):
            print("Converting LazyFrame to DataFrame...")
            cla_input_df = cla_input_df.collect()
        elif hasattr(cla_input_df, 'to_pandas'):
            print("Converting pandas DataFrame to Polars...")
            cla_input_df = pl.from_pandas(cla_input_df)

    print("Initial conversion completed in", f"{time.time() - start_time:.2f}", "seconds")
    print("Processing NULL values and casting types...")

    # First convert numeric columns to strings to handle NULL values
    cla_input_df = cla_input_df.with_columns([
        pl.col('ProcessingDateKey').cast(pl.Int64),
        pl.col('CommitmentAmt').cast(pl.Utf8),
        pl.col('OutstandingAmt').cast(pl.Utf8)
    ])

    # Then handle NULL values and convert to float
    cla_input_df = cla_input_df.with_columns([
        pl.when(pl.col('CommitmentAmt').is_null() | (pl.col('CommitmentAmt') == 'NULL'))
        .then(None)
        .otherwise(pl.col('CommitmentAmt'))
        .cast(pl.Float64)
        .alias('CommitmentAmt'),

        pl.when(pl.col('OutstandingAmt').is_null() | (pl.col('OutstandingAmt') == 'NULL'))
        .then(None)
        .otherwise(pl.col('OutstandingAmt'))
        .cast(pl.Float64)
        .alias('OutstandingAmt')
    ])

    agg_start = time.time()
    print("Starting aggregation...")

    # Calculate the raw amounts using Polars
    cla_test_df = (cla_input_df.lazy()
                   .group_by('ProcessingDateKey')
                   .agg([
        pl.col('CommitmentAmt').sum().cast(pl.Float64).alias('CommitmentAmt'),
        pl.col('CommitmentAmt').count().cast(pl.Int64).alias('Deals'),
        pl.col('OutstandingAmt').sum().cast(pl.Float64).alias('OutstandingAmt')
    ])
                   .sort('ProcessingDateKey')
                   .collect())

    print("Aggregation completed in", f"{time.time() - agg_start:.2f}", "seconds")
    print(f"cla_test_df has {len(cla_test_df)} rows")

    processing_start = time.time()

    # Create prior period mapping
    date_list = cla_test_df['ProcessingDateKey'].to_list()
    date_prior_list = [0] + date_list[:-1]

    # Add prior period data
    cla_test_df = cla_test_df.with_columns([
        pl.Series('ProcessingDateKeyPrior', date_prior_list).cast(pl.Int64)
    ])

    # Join with prior period data
    cla_test_df = cla_test_df.join(
        cla_test_df.select([
            pl.col('ProcessingDateKey'),
            pl.col('CommitmentAmt').alias('CommitmentAmtPrior'),
            pl.col('OutstandingAmt').alias('OutstandingAmtPrior'),
            pl.col('Deals').alias('DealsPrior')
        ]),
        left_on='ProcessingDateKeyPrior',
        right_on='ProcessingDateKey',
        how='left'
    )

    # Calculate differences with explicit casting and null handling
    print("Calculating differences...")
    cla_test_df = cla_test_df.with_columns([
        pl.when(pl.col('CommitmentAmtPrior').is_null() | (pl.col('CommitmentAmtPrior') == 0))
        .then(None)
        .otherwise((pl.col('CommitmentAmt') / pl.col('CommitmentAmtPrior')) - 1)
        .alias('ca_diff'),

        pl.when(pl.col('OutstandingAmtPrior').is_null() | (pl.col('OutstandingAmtPrior') == 0))
        .then(None)
        .otherwise((pl.col('OutstandingAmt') / pl.col('OutstandingAmtPrior')) - 1)
        .alias('oa_diff'),

        pl.when(pl.col('DealsPrior').is_null() | (pl.col('DealsPrior') == 0))
        .then(None)
        .otherwise((pl.col('Deals').cast(pl.Float64) / pl.col('DealsPrior').cast(pl.Float64)) - 1)
        .alias('deals_diff')
    ])

    # Convert to lists properly, ensuring lengths match
    if hasattr(ca_perc_diff, 'to_list'):
        ca_values = ca_perc_diff.to_list()
        oa_values = oa_perc_diff.to_list()
        deals_values = deals_perc_diff.to_list()
    else:
        ca_values = list(ca_perc_diff)
        oa_values = list(oa_perc_diff)
        deals_values = list(deals_perc_diff)

    # Ensure lengths match - pad with NaN if needed
    target_length = len(cla_test_df)
    print(f"Target length: {target_length}")
    print(f"ca_values length: {len(ca_values)}")

    if len(ca_values) < target_length:
        ca_values.extend([np.nan] * (target_length - len(ca_values)))
        oa_values.extend([np.nan] * (target_length - len(oa_values)))
        deals_values.extend([np.nan] * (target_length - len(deals_values)))
        print(f"Padded values to length {target_length}")
    elif len(ca_values) > target_length:
        ca_values = ca_values[:target_length]
        oa_values = oa_values[:target_length]
        deals_values = deals_values[:target_length]
        print(f"Truncated values to length {target_length}")

    # Add model differences
    cla_test_df = cla_test_df.with_columns([
        pl.Series('ca_model_diff', ca_values).cast(pl.Float64),
        pl.Series('oa_model_diff', oa_values).cast(pl.Float64),
        pl.Series('deals_model_diff', deals_values).cast(pl.Float64)
    ])

    print("Processing completed in", f"{time.time() - processing_start:.2f}", "seconds")

    # Save output if filename provided
    if file_name:
        save_start = time.time()
        cla_test_df.write_csv(file_name)
        print("Results saved to", file_name, "in", f"{time.time() - save_start:.2f}", "seconds")
    else:
        print(cla_test_df)

    total_time = time.time() - start_time
    print("Total execution time:", f"{total_time:.2f}", "seconds")

    return cla_test_df


if __name__ == "__main__":
    # Example of key columns that might be needed (now including the new filter columns)
    essential_columns = [
        "ProcessingDateKey",
        "CommitmentAmt",
        "OutstandingAmt",
        "Region",
        "NAICSGrpName",
        "LineofBusinessId",
        "CommitmentSizeGroup",
        "BankID",
        "RiskGroupDesc"
    ]

    # Load all filter options for dashboarding
    print("=== Loading Filter Options for Dashboard ===")
    filter_options = get_all_filter_options(use_polars=True)

    if filter_options:
        print("\nAvailable filter options loaded:")

        print("\nRegions (", len(filter_options['regions']), "options):")
        for region_name in filter_options['regions'][:5]:
            print("  -", region_name)
        if len(filter_options['regions']) > 5:
            print("  ... and", len(filter_options['regions']) - 5, "more")

        print("\nSBA Classifications:")
        for sba_class in filter_options['sba_classifications']:
            print("  -", sba_class)

        print("\nLine of Business IDs (", len(filter_options['line_of_business_ids']), "options):")
        for lob in filter_options['line_of_business_ids'][:5]:
            print("  -", lob['display_name'], f"({lob['record_count']:,} records)")
        if len(filter_options['line_of_business_ids']) > 5:
            print("  ... and", len(filter_options['line_of_business_ids']) - 5, "more")

        print("\nCommitment Size Groups (", len(filter_options['commitment_size_groups']), "options):")
        for csg in filter_options['commitment_size_groups'][:5]:
            print("  -", csg)
        if len(filter_options['commitment_size_groups']) > 5:
            print("  ... and", len(filter_options['commitment_size_groups']) - 5, "more")

        print("\nRisk Group Descriptions (", len(filter_options['risk_group_descriptions']), "options):")
        for rgd in filter_options['risk_group_descriptions'][:5]:
            print("  -", rgd)
        if len(filter_options['risk_group_descriptions']) > 5:
            print("  ... and", len(filter_options['risk_group_descriptions']) - 5, "more")

    # Example 1: SBA Classification filter only (broader filter)
    print("\n=== Example 1: SBA Classification Filter Only ===")
    sba_only_data = get_data_optimized(
        selected_columns=essential_columns,
        region='Rocky Mountain',
        sba_filter='Non-SBA',  # This filters to all Non-SBA line of business
        row_limit=1000
    )

    if sba_only_data is not None:
        print("SBA-only filtered data shape:", sba_only_data.shape)
        # Show unique line of business IDs in the result
        if hasattr(sba_only_data, 'select'):  # Polars
            unique_lobs = sba_only_data.select("LineofBusinessId").unique().sort("LineofBusinessId")
            unique_lob_list = unique_lobs['LineofBusinessId'].to_list()
            print("Unique Line of Business IDs in Non-SBA data:", unique_lob_list)
        else:  # pandas
            unique_lobs = sorted(sba_only_data['LineofBusinessId'].unique())
            print("Unique Line of Business IDs in Non-SBA data:", unique_lobs)
            unique_lob_list = unique_lobs

        # Example 2: Both SBA Classification AND specific Line of Business IDs (more specific filter)
        # Use the actual LOB IDs found in the data
        if unique_lob_list:
            # Take first 2 available LOB IDs from the actual data
            available_lobs = unique_lob_list[:2]
            print("\n=== Example 2: SBA Classification + Specific Line of Business IDs ===")
            print("Using available LOB IDs:", available_lobs)

            combined_lob_data = get_data_optimized(
                selected_columns=essential_columns,
                region='Rocky Mountain',
                sba_filter='Non-SBA',  # First filter to Non-SBA
                line_of_business_ids=available_lobs,  # Use actual LOB IDs from the data
                commitment_size_groups=['Small', 'Medium'],  # This might also need adjustment based on actual data
                row_limit=1000
            )

            if combined_lob_data is not None:
                print("Combined filtered data shape:", combined_lob_data.shape)

                # Show breakdown by the filters
                if hasattr(combined_lob_data, 'group_by'):  # Polars
                    filter_breakdown = combined_lob_data.group_by(
                        ["LineofBusinessId", "CommitmentSizeGroup"]
                    ).agg(pl.count().alias("Count")).sort(["LineofBusinessId", "CommitmentSizeGroup"])
                    print("Filter breakdown:")
                    print(filter_breakdown)
                else:  # pandas
                    filter_breakdown = combined_lob_data.groupby(
                        ["LineofBusinessId", "CommitmentSizeGroup"]
                    ).size().reset_index(name="Count")
                    print("Filter breakdown:")
                    print(filter_breakdown)
            else:
                print("No data returned - possibly due to commitment size group filter")
                print("Trying without commitment size group filter...")

                # Try again without commitment size group filter
                combined_lob_data_retry = get_data_optimized(
                    selected_columns=essential_columns,
                    region='Rocky Mountain',
                    sba_filter='Non-SBA',
                    line_of_business_ids=available_lobs,
                    row_limit=1000
                )

                if combined_lob_data_retry is not None:
                    print("Retry without commitment size filter - shape:", combined_lob_data_retry.shape)

    # Example 3: SBA data with specific Line of Business (should only return LOB 12)
    print("\n=== Example 3: SBA Classification with Specific LOB (Conflicting) ===")
    conflicting_data = get_data_optimized(
        selected_columns=essential_columns,
        region='Rocky Mountain',
        sba_filter='SBA',  # This forces LineofBusinessId = '12'
        line_of_business_ids=['1', '2'],  # These are Non-SBA LOBs - should conflict
        row_limit=1000
    )

    if conflicting_data is not None:
        print("Conflicting filter data shape:", conflicting_data.shape)
        print("Note: This should return no data due to conflicting filters")
    else:
        print("No data returned - expected due to conflicting SBA and LOB ID filters")

    print("\n=== Filter Usage Summary ===")
    print("1. SBA Classification Filter ('sba_filter'):")
    print("   - 'All': No SBA filtering")
    print("   - 'SBA': Only LineofBusinessId = '12'")
    print("   - 'Non-SBA': Only LineofBusinessId != '12'")
    print("")
    print("2. Line of Business ID Filter ('line_of_business_ids'):")
    print("   - Filters to specific LineofBusinessId values")
    print("   - Works in combination with SBA filter")
    print("   - Use when you want specific business lines within SBA/Non-SBA")
    print(
        f"   - Available Non-SBA LOB IDs in Rocky Mountain: {unique_lob_list if 'unique_lob_list' in locals() else 'Run Example 1 first to see available IDs'}")
    print("")
    print("3. Other Filters:")
    print("   - 'commitment_size_groups': Filter by deal size")
    print("   - 'risk_group_descriptions': Filter by risk categories")
    print("   - All filters can be single values or lists")
    print("")
    print("Important: Use actual values from the database, not zero-padded versions!")
    print("LineofBusinessId values are stored as: '1', '2', '5', '12', etc.")
    print("NOT as: '01', '02', '05', '12', etc.")