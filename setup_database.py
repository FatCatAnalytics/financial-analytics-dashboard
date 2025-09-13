#!/usr/bin/env python3
"""
Database setup script to create PostgreSQL table and import sample.csv data
"""

import pandas as pd
import psycopg2
from psycopg2 import sql
import os
from datetime import datetime
import numpy as np

def create_database_connection():
    """Create connection to PostgreSQL database"""
    try:
        # Database configuration - you can modify these or use environment variables
        DB_CONFIG = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'volume_composites'),
            'user': os.getenv('DB_USER', os.getenv('USER', 'postgres')),
            'password': os.getenv('DB_PASSWORD', '')
        }
        
        print(f"Connecting to PostgreSQL at {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        print(f"Database: {DB_CONFIG['database']}, User: {DB_CONFIG['user']}")
        
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Successfully connected to PostgreSQL database!")
        return conn
        
    except psycopg2.Error as e:
        print(f"❌ Error connecting to PostgreSQL database: {e}")
        print("\n📝 To set up PostgreSQL:")
        print("1. Install PostgreSQL: brew install postgresql (macOS) or apt-get install postgresql (Ubuntu)")
        print("2. Start PostgreSQL service: brew services start postgresql")
        print("3. Create database: createdb volume_composites")
        print("4. Set environment variables or update DB_CONFIG in this script")
        return None

def create_table_schema(conn):
    """Create the main analytics table based on sample.csv structure"""
    
    create_table_sql = """
    DROP TABLE IF EXISTS analytics_data CASCADE;
    
    CREATE TABLE analytics_data (
        id SERIAL PRIMARY KEY,
        ProcessingDateKey BIGINT NOT NULL,
        CommitmentAmt DECIMAL(15,2),
        OutstandingAmt DECIMAL(15,2),
        Region VARCHAR(50),
        NAICSGrpName VARCHAR(100),
        CommitmentSizeGroup VARCHAR(50),
        RiskGroupDesc VARCHAR(50),
        LineofBusinessId VARCHAR(10),
        CurrentMaturityDateKey BIGINT,
        BankID VARCHAR(10),
        size_SortOrder INTEGER,
        MaturityTermMonths INTEGER,
        tenor_SortOrder INTEGER,
        SpreadBPS DECIMAL(10,2),
        YieldPct DECIMAL(8,6),
        TotalCreditRelationship DECIMAL(15,2),
        RelativeValue INTEGER,
        LineofBusiness VARCHAR(50),
        NAICSGrpCode INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create indexes for better query performance
    CREATE INDEX idx_analytics_processing_date ON analytics_data(ProcessingDateKey);
    CREATE INDEX idx_analytics_region ON analytics_data(Region);
    CREATE INDEX idx_analytics_lob ON analytics_data(LineofBusinessId);
    CREATE INDEX idx_analytics_bank ON analytics_data(BankID);
    CREATE INDEX idx_analytics_commitment_size ON analytics_data(CommitmentSizeGroup);
    CREATE INDEX idx_analytics_risk_group ON analytics_data(RiskGroupDesc);
    
    -- Create a view for easier querying
    CREATE OR REPLACE VIEW analytics_summary AS
    SELECT 
        ProcessingDateKey,
        COUNT(*) as Deals,
        SUM(CommitmentAmt) as CommitmentAmt,
        SUM(OutstandingAmt) as OutstandingAmt,
        AVG(CommitmentAmt) as AvgCommitmentAmt,
        Region,
        LineofBusinessId,
        LineofBusiness,
        CommitmentSizeGroup,
        RiskGroupDesc
    FROM analytics_data 
    WHERE CommitmentAmt IS NOT NULL
    GROUP BY ProcessingDateKey, Region, LineofBusinessId, LineofBusiness, CommitmentSizeGroup, RiskGroupDesc
    ORDER BY ProcessingDateKey, CommitmentAmt DESC;
    """
    
    try:
        cursor = conn.cursor()
        cursor.execute(create_table_sql)
        conn.commit()
        cursor.close()
        print("✅ Successfully created analytics_data table and indexes!")
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Error creating table: {e}")
        return False

def load_csv_data(conn, csv_file_path):
    """Load data from sample.csv into PostgreSQL"""
    
    if not os.path.exists(csv_file_path):
        print(f"❌ CSV file not found: {csv_file_path}")
        return False
    
    try:
        # Read CSV file
        print(f"📖 Reading CSV file: {csv_file_path}")
        df = pd.read_csv(csv_file_path, sep='\t')  # Tab-separated based on your sample
        print(f"✅ Loaded {len(df)} rows from CSV")
        
        # Clean and prepare data
        print("🧹 Cleaning data...")
        
        # Handle NULL strings and convert to proper nulls
        df = df.replace(['NULL', 'null', ''], np.nan)
        
        # Convert date columns to integers (YYYYMMDD format)
        if 'ProcessingDateKey' in df.columns:
            df['ProcessingDateKey'] = pd.to_numeric(df['ProcessingDateKey'], errors='coerce').astype('Int64')
        
        if 'CurrentMaturityDateKey' in df.columns:
            df['CurrentMaturityDateKey'] = pd.to_numeric(df['CurrentMaturityDateKey'], errors='coerce')
            # Handle -1 values (invalid dates)
            df.loc[df['CurrentMaturityDateKey'] == -1, 'CurrentMaturityDateKey'] = None
            df['CurrentMaturityDateKey'] = df['CurrentMaturityDateKey'].astype('Int64')
        
        # Convert numeric columns
        numeric_columns = ['CommitmentAmt', 'OutstandingAmt', 'SpreadBPS', 'YieldPct', 
                          'TotalCreditRelationship', 'MaturityTermMonths']
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Insert data in batches
        cursor = conn.cursor()
        batch_size = 1000
        total_inserted = 0
        
        print(f"📥 Inserting data in batches of {batch_size}...")
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            
            # Prepare insert statement
            insert_sql = """
            INSERT INTO analytics_data (
                ProcessingDateKey, CommitmentAmt, OutstandingAmt, Region, NAICSGrpName,
                CommitmentSizeGroup, RiskGroupDesc, LineofBusinessId, CurrentMaturityDateKey,
                BankID, size_SortOrder, MaturityTermMonths, tenor_SortOrder, SpreadBPS,
                YieldPct, TotalCreditRelationship, RelativeValue, LineofBusiness, NAICSGrpCode
            ) VALUES %s
            """
            
            # Prepare values with proper None handling
            values = []
            for idx, row in batch.iterrows():
                try:
                    values.append((
                        int(row.get('ProcessingDateKey')) if pd.notna(row.get('ProcessingDateKey')) else None,
                        float(row.get('CommitmentAmt')) if pd.notna(row.get('CommitmentAmt')) else None,
                        float(row.get('OutstandingAmt')) if pd.notna(row.get('OutstandingAmt')) else None,
                        str(row.get('Region')) if pd.notna(row.get('Region')) else None,
                        str(row.get('NAICSGrpName')) if pd.notna(row.get('NAICSGrpName')) else None,
                        str(row.get('CommitmentSizeGroup')) if pd.notna(row.get('CommitmentSizeGroup')) else None,
                        str(row.get('RiskGroupDesc')) if pd.notna(row.get('RiskGroupDesc')) else None,
                        str(row.get('LineofBusinessId')) if pd.notna(row.get('LineofBusinessId')) else None,
                        int(row.get('CurrentMaturityDateKey')) if pd.notna(row.get('CurrentMaturityDateKey')) else None,
                        str(row.get('BankID')) if pd.notna(row.get('BankID')) else None,
                        int(row.get('size_SortOrder')) if pd.notna(row.get('size_SortOrder')) else None,
                        int(row.get('MaturityTermMonths')) if pd.notna(row.get('MaturityTermMonths')) else None,
                        int(row.get('tenor_SortOrder')) if pd.notna(row.get('tenor_SortOrder')) else None,
                        float(row.get('SpreadBPS')) if pd.notna(row.get('SpreadBPS')) else None,
                        float(row.get('YieldPct')) if pd.notna(row.get('YieldPct')) else None,
                        float(row.get('TotalCreditRelationship')) if pd.notna(row.get('TotalCreditRelationship')) else None,
                        int(row.get('RelativeValue')) if pd.notna(row.get('RelativeValue')) else None,
                        str(row.get('LineofBusiness')) if pd.notna(row.get('LineofBusiness')) else None,
                        int(row.get('NAICSGrpCode')) if pd.notna(row.get('NAICSGrpCode')) else None
                    ))
                except Exception as e:
                    print(f"Error processing row {idx}: {e}")
                    print(f"Row data: {row.to_dict()}")
                    continue
            
            # Execute batch insert
            from psycopg2.extras import execute_values
            execute_values(cursor, insert_sql, values, template=None, page_size=100)
            
            total_inserted += len(batch)
            print(f"  ✅ Inserted batch {i//batch_size + 1}: {total_inserted}/{len(df)} rows")
        
        conn.commit()
        cursor.close()
        
        print(f"🎉 Successfully inserted {total_inserted} rows into analytics_data table!")
        return True
        
    except Exception as e:
        print(f"❌ Error loading CSV data: {e}")
        conn.rollback()
        return False

def create_aggregated_view(conn):
    """Create aggregated view similar to your existing analytics data"""
    
    aggregation_sql = """
    -- Create aggregated analytics view that matches your frontend expectations
    CREATE OR REPLACE VIEW aggregated_analytics AS
    WITH monthly_data AS (
        SELECT 
            ProcessingDateKey,
            COUNT(*) as Deals,
            SUM(CommitmentAmt) as CommitmentAmt,
            SUM(OutstandingAmt) as OutstandingAmt
        FROM analytics_data 
        WHERE CommitmentAmt IS NOT NULL 
        GROUP BY ProcessingDateKey
        ORDER BY ProcessingDateKey
    ),
    with_prior AS (
        SELECT *,
            LAG(ProcessingDateKey) OVER (ORDER BY ProcessingDateKey) as ProcessingDateKeyPrior,
            LAG(CommitmentAmt) OVER (ORDER BY ProcessingDateKey) as CommitmentAmtPrior,
            LAG(OutstandingAmt) OVER (ORDER BY ProcessingDateKey) as OutstandingAmtPrior,
            LAG(Deals) OVER (ORDER BY ProcessingDateKey) as DealsPrior
        FROM monthly_data
    )
    SELECT 
        ProcessingDateKey::varchar as ProcessingDateKey,
        CommitmentAmt,
        Deals,
        OutstandingAmt,
        COALESCE(ProcessingDateKeyPrior::varchar, '0') as ProcessingDateKeyPrior,
        COALESCE(CommitmentAmtPrior, 0) as CommitmentAmtPrior,
        COALESCE(OutstandingAmtPrior, 0) as OutstandingAmtPrior,
        COALESCE(DealsPrior, 0) as DealsPrior,
        -- Calculate percentage differences
        CASE 
            WHEN CommitmentAmtPrior > 0 THEN (CommitmentAmt - CommitmentAmtPrior) / CommitmentAmtPrior
            ELSE NULL 
        END as ca_diff,
        CASE 
            WHEN OutstandingAmtPrior > 0 THEN (OutstandingAmt - OutstandingAmtPrior) / OutstandingAmtPrior
            ELSE NULL 
        END as oa_diff,
        CASE 
            WHEN DealsPrior > 0 THEN (Deals::float - DealsPrior::float) / DealsPrior::float
            ELSE NULL 
        END as deals_diff,
        -- Placeholder model differences (can be calculated later)
        NULL::float as ca_model_diff,
        NULL::float as oa_model_diff,
        NULL::float as deals_model_diff
    FROM with_prior
    ORDER BY ProcessingDateKey;
    """
    
    try:
        cursor = conn.cursor()
        cursor.execute(aggregation_sql)
        conn.commit()
        cursor.close()
        print("✅ Successfully created aggregated_analytics view!")
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Error creating aggregated view: {e}")
        return False

def test_database_setup(conn):
    """Test the database setup by running some queries"""
    
    try:
        cursor = conn.cursor()
        
        # Test 1: Count total records
        cursor.execute("SELECT COUNT(*) FROM analytics_data")
        total_records = cursor.fetchone()[0]
        print(f"📊 Total records in analytics_data: {total_records:,}")
        
        # Test 2: Check date range
        cursor.execute("SELECT MIN(ProcessingDateKey), MAX(ProcessingDateKey) FROM analytics_data")
        min_date, max_date = cursor.fetchone()
        print(f"📅 Date range: {min_date} to {max_date}")
        
        # Test 3: Check regions
        cursor.execute("SELECT DISTINCT Region FROM analytics_data WHERE Region IS NOT NULL ORDER BY Region")
        regions = [row[0] for row in cursor.fetchall()]
        print(f"🌍 Available regions: {', '.join(regions)}")
        
        # Test 4: Check line of business
        cursor.execute("SELECT DISTINCT LineofBusinessId, LineofBusiness FROM analytics_data WHERE LineofBusinessId IS NOT NULL ORDER BY LineofBusinessId")
        lobs = cursor.fetchall()
        print(f"💼 Line of Business options:")
        for lob_id, lob_name in lobs:
            print(f"  - {lob_id}: {lob_name}")
        
        # Test 5: Test aggregated view
        cursor.execute("SELECT COUNT(*) FROM aggregated_analytics")
        agg_records = cursor.fetchone()[0]
        print(f"📈 Aggregated analytics records: {agg_records}")
        
        # Test 6: Sample aggregated data
        cursor.execute("SELECT * FROM aggregated_analytics ORDER BY ProcessingDateKey DESC LIMIT 3")
        sample_data = cursor.fetchall()
        print(f"📋 Sample aggregated data (latest 3 months):")
        for row in sample_data:
            print(f"  - {row[0]}: ${row[1]:,.0f} commitment, {row[2]:,} deals")
        
        cursor.close()
        print("✅ Database setup test completed successfully!")
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Error testing database: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Starting PostgreSQL database setup for Volume Composites...")
    print("="*60)
    
    # Step 1: Connect to database
    conn = create_database_connection()
    if not conn:
        return False
    
    # Step 2: Create table schema
    if not create_table_schema(conn):
        conn.close()
        return False
    
    # Step 3: Load CSV data
    csv_path = "/Users/aetingu/Volume Composites/sample.csv"
    if not load_csv_data(conn, csv_path):
        conn.close()
        return False
    
    # Step 4: Create aggregated view
    if not create_aggregated_view(conn):
        conn.close()
        return False
    
    # Step 5: Test setup
    if not test_database_setup(conn):
        conn.close()
        return False
    
    conn.close()
    
    print("="*60)
    print("🎉 Database setup completed successfully!")
    print("\n📝 Next steps:")
    print("1. Update your .env file with database credentials")
    print("2. Test the backend APIs")
    print("3. Update frontend to use backend APIs")
    print("\n💡 Connection details:")
    print("- Host: localhost")
    print("- Port: 5432") 
    print("- Database: volume_composites")
    print("- Main table: analytics_data")
    print("- Aggregated view: aggregated_analytics")
    
    return True

if __name__ == "__main__":
    main()
