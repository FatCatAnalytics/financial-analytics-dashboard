import pandas as pd
import numpy as np
from datetime import datetime
import json
from typing import Dict, List, Any

def load_and_process_csv(file_path: str = "test-2.csv") -> Dict[str, Any]:
    """
    Load and process the CSV data for the dashboard
    """
    try:
        # Read CSV with tab separator
        df = pd.read_csv(file_path, sep='\t')
        
        print(f"Loaded {len(df)} records from {file_path}")
        print(f"Columns: {list(df.columns)}")
        
        # Convert ProcessingDateKey to datetime
        df['ProcessingDateKey'] = pd.to_datetime(df['ProcessingDateKey'], format='%Y%m%d')
        
        # Get unique values for filters
        filter_options = {
            "lineOfBusiness": sorted(df['LineofBusiness'].dropna().unique().tolist()),
            "commitmentSizeGroup": sorted(df['CommitmentSizeGroup'].dropna().unique().tolist()),
            "riskGroup": sorted(df['RiskGroupDesc'].dropna().unique().tolist()),
            "bankId": sorted(df['BankID'].dropna().astype(str).unique().tolist()),
            "region": sorted(df['Region'].dropna().unique().tolist()),
            "naicsGrpName": sorted(df['NAICSGrpName'].dropna().unique().tolist())
        }
        
        # Aggregate data by ProcessingDateKey for time series analysis
        monthly_data = df.groupby('ProcessingDateKey').agg({
            'CommitmentAmt': 'sum',
            'OutstandingAmt': 'sum',
            'BankID': 'count'  # Count of deals
        }).reset_index()
        
        monthly_data = monthly_data.rename(columns={'BankID': 'Deals'})
        monthly_data = monthly_data.sort_values('ProcessingDateKey')
        
        # Calculate period-over-period changes
        monthly_data['ProcessingDateKeyPrior'] = monthly_data['ProcessingDateKey'].shift(1)
        monthly_data['CommitmentAmtPrior'] = monthly_data['CommitmentAmt'].shift(1)
        monthly_data['OutstandingAmtPrior'] = monthly_data['OutstandingAmt'].shift(1)
        monthly_data['DealsPrior'] = monthly_data['Deals'].shift(1)
        
        # Calculate differences
        monthly_data['ca_diff'] = monthly_data.apply(
            lambda row: (row['CommitmentAmt'] - row['CommitmentAmtPrior']) / row['CommitmentAmtPrior'] 
            if pd.notna(row['CommitmentAmtPrior']) and row['CommitmentAmtPrior'] != 0 else None, axis=1
        )
        
        monthly_data['oa_diff'] = monthly_data.apply(
            lambda row: (row['OutstandingAmt'] - row['OutstandingAmtPrior']) / row['OutstandingAmtPrior'] 
            if pd.notna(row['OutstandingAmtPrior']) and row['OutstandingAmtPrior'] != 0 else None, axis=1
        )
        
        monthly_data['deals_diff'] = monthly_data.apply(
            lambda row: (row['Deals'] - row['DealsPrior']) / row['DealsPrior'] 
            if pd.notna(row['DealsPrior']) and row['DealsPrior'] != 0 else None, axis=1
        )
        
        # Add mock model differences (in real scenario, these would come from your models)
        np.random.seed(42)  # For reproducible results
        monthly_data['ca_model_diff'] = np.random.normal(0, 0.05, len(monthly_data))
        monthly_data['oa_model_diff'] = np.random.normal(0, 0.04, len(monthly_data))
        monthly_data['deals_model_diff'] = np.random.normal(0, 0.03, len(monthly_data))
        
        # Convert dates to strings for JSON serialization
        monthly_data['ProcessingDateKey'] = monthly_data['ProcessingDateKey'].dt.strftime('%Y-%m-%d')
        monthly_data['ProcessingDateKeyPrior'] = monthly_data['ProcessingDateKeyPrior'].dt.strftime('%Y-%m-%d').fillna('0')
        
        # Fill NaN values
        monthly_data = monthly_data.fillna(0)
        
        # Convert to list of dictionaries for API response
        analytics_data = monthly_data.to_dict('records')
        
        # Get summary statistics
        total_commitment = df['CommitmentAmt'].sum()
        total_outstanding = df['OutstandingAmt'].sum()
        total_deals = len(df)
        latest_period = monthly_data['ProcessingDateKey'].iloc[-1] if len(monthly_data) > 0 else None
        
        summary = {
            "total_commitment": total_commitment,
            "total_outstanding": total_outstanding,
            "total_deals": total_deals,
            "latest_period": latest_period,
            "date_range": {
                "start": monthly_data['ProcessingDateKey'].iloc[0] if len(monthly_data) > 0 else None,
                "end": monthly_data['ProcessingDateKey'].iloc[-1] if len(monthly_data) > 0 else None
            },
            "record_count": len(analytics_data)
        }
        
        return {
            "filter_options": filter_options,
            "analytics_data": analytics_data,
            "raw_data": df.to_dict('records'),
            "summary": summary
        }
        
    except Exception as e:
        print(f"Error processing CSV: {e}")
        return {
            "filter_options": {},
            "analytics_data": [],
            "raw_data": [],
            "summary": {},
            "error": str(e)
        }

def filter_data(df_records: List[Dict], filters: Dict[str, Any]) -> List[Dict]:
    """
    Apply filters to the raw data
    """
    if not df_records:
        return []
    
    df = pd.DataFrame(df_records)
    
    # Apply filters
    if filters.get('region') and filters['region'] != ['All']:
        df = df[df['Region'].isin(filters['region'])]
    
    if filters.get('lineOfBusiness') and filters['lineOfBusiness'] != ['All']:
        df = df[df['LineofBusiness'].isin(filters['lineOfBusiness'])]
    
    if filters.get('commitmentSizeGroup') and filters['commitmentSizeGroup'] != ['All']:
        df = df[df['CommitmentSizeGroup'].isin(filters['commitmentSizeGroup'])]
    
    if filters.get('riskGroup') and filters['riskGroup'] != ['All']:
        df = df[df['RiskGroupDesc'].isin(filters['riskGroup'])]
    
    if filters.get('bankId') and filters['bankId'] != ['All']:
        bank_ids = [str(bid) for bid in filters['bankId']]
        df = df[df['BankID'].astype(str).isin(bank_ids)]
    
    if filters.get('naicsGrpName') and filters['naicsGrpName'] != ['All']:
        df = df[df['NAICSGrpName'].isin(filters['naicsGrpName'])]
    
    return df.to_dict('records')

if __name__ == "__main__":
    # Test the data processing
    result = load_and_process_csv()
    print(f"\nProcessed data summary:")
    print(f"Filter options: {len(result['filter_options'])} categories")
    print(f"Analytics data: {len(result['analytics_data'])} time periods")
    print(f"Raw data: {len(result['raw_data'])} records")
    print(f"Summary: {result['summary']}")
    
    # Save processed data for API to use
    with open('processed_data.json', 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    print("\nSaved processed data to processed_data.json")
