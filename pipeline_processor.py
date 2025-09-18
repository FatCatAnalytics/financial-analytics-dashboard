#!/usr/bin/env python3
"""
Pipeline Processor for Volume Composites Analysis
This script runs the capped vs uncapped analysis with templated parameters
and outputs CSV files for use in compute engine pipelines.

Usage:
    python pipeline_processor.py --template template1
    python pipeline_processor.py --custom --region "Rocky Mountain" --sba-filter "Non-SBA"
    python pipeline_processor.py --all-templates
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd
import polars as pl
from dotenv import load_dotenv

# Import the main analysis functions
from main import (
    get_db_connection_uri,
    read_sql_polars,
    setup_groups,
    testCappedvsUncapped
)

# Load environment variables
load_dotenv()

# Define analysis templates
ANALYSIS_TEMPLATES = {
    "template1": {
        "name": "Non-SBA Rocky Mountain",
        "description": "Non-SBA classification with Rocky Mountain region",
        "filters": {
            "sba_classification": "Non-SBA",
            "region": "Rocky Mountain",
            "line_of_business_ids": None,
            "commitment_size_groups": None,
            "risk_group_descriptions": None
        }
    },
    "template2": {
        "name": "Non-SBA High Quality",
        "description": "Non-SBA all regions with High Quality risk group",
        "filters": {
            "sba_classification": "Non-SBA",
            "region": None,  # All regions
            "line_of_business_ids": None,
            "commitment_size_groups": None,
            "risk_group_descriptions": ["High Quality"]
        }
    },
    "template3": {
        "name": "SBA All Regions",
        "description": "SBA classification across all regions",
        "filters": {
            "sba_classification": "SBA",
            "region": None,
            "line_of_business_ids": None,
            "commitment_size_groups": None,
            "risk_group_descriptions": None
        }
    },
    "template4": {
        "name": "Large Commitments High Risk",
        "description": "Large commitment sizes with high risk groups",
        "filters": {
            "sba_classification": None,  # All
            "region": None,
            "line_of_business_ids": None,
            "commitment_size_groups": ["$5MM - $10MM", "$10MM - $25MM", "> $25MM"],
            "risk_group_descriptions": ["Substandard", "Doubtful", "Loss"]
        }
    },
    "template5": {
        "name": "Southwest Non-SBA Medium Size",
        "description": "Southwest region Non-SBA with medium commitment sizes",
        "filters": {
            "sba_classification": "Non-SBA",
            "region": "Southwest",
            "line_of_business_ids": None,
            "commitment_size_groups": ["$1MM - $5MM", "$5MM - $10MM"],
            "risk_group_descriptions": None
        }
    }
}


class PipelineProcessor:
    """Main processor class for running templated analysis"""
    
    def __init__(self, output_dir: str = "pipeline_output"):
        """Initialize the processor with output directory"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.connection_uri = None
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def connect_database(self) -> bool:
        """Establish database connection"""
        try:
            self.connection_uri = get_db_connection_uri()
            if not self.connection_uri:
                print("❌ Failed to get database connection URI")
                return False
            print("✅ Database connection established")
            return True
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            return False
    
    def build_query(self, filters: Dict[str, Any]) -> str:
        """Build SQL query based on filters"""
        where_conditions = []
        
        # SBA Classification filter
        if filters.get("sba_classification"):
            if filters["sba_classification"] == "SBA":
                where_conditions.append("lineofbusinessid = '12'")
            elif filters["sba_classification"] == "Non-SBA":
                where_conditions.append("lineofbusinessid != '12'")
        
        # Region filter
        if filters.get("region"):
            where_conditions.append(f"region = '{filters['region']}'")
        
        # Line of Business IDs filter
        if filters.get("line_of_business_ids"):
            lob_list = filters["line_of_business_ids"]
            if isinstance(lob_list, list):
                lob_str = "','".join(lob_list)
                where_conditions.append(f"lineofbusinessid IN ('{lob_str}')")
            else:
                where_conditions.append(f"lineofbusinessid = '{lob_list}'")
        
        # Commitment Size Groups filter
        if filters.get("commitment_size_groups"):
            csg_list = filters["commitment_size_groups"]
            if isinstance(csg_list, list):
                csg_str = "','".join(csg_list)
                where_conditions.append(f"commitmentsizegroup IN ('{csg_str}')")
            else:
                where_conditions.append(f"commitmentsizegroup = '{csg_list}'")
        
        # Risk Group Descriptions filter
        if filters.get("risk_group_descriptions"):
            rgd_list = filters["risk_group_descriptions"]
            if isinstance(rgd_list, list):
                rgd_str = "','".join(rgd_list)
                where_conditions.append(f"riskgroupdesc IN ('{rgd_str}')")
            else:
                where_conditions.append(f"riskgroupdesc = '{rgd_list}'")
        
        # Date filters (ProcessingDateKey only)
        if filters.get("date_filters"):
            from datetime import datetime
            for date_filter in filters["date_filters"]:
                operator = date_filter.get("operator")
                
                try:
                    # Convert ISO date string to YYYYMMDD format
                    start_date = datetime.fromisoformat(date_filter.get("startDate", "").replace('Z', '+00:00'))
                    start_date_key = int(start_date.strftime('%Y%m%d'))
                    
                    if operator == "equals":
                        where_conditions.append(f"processingdatekey = {start_date_key}")
                    elif operator == "greaterThan":
                        where_conditions.append(f"processingdatekey >= {start_date_key}")
                    elif operator == "lessThan":
                        where_conditions.append(f"processingdatekey <= {start_date_key}")
                    elif operator == "between" and date_filter.get("endDate"):
                        end_date = datetime.fromisoformat(date_filter.get("endDate", "").replace('Z', '+00:00'))
                        end_date_key = int(end_date.strftime('%Y%m%d'))
                        where_conditions.append(f"processingdatekey BETWEEN {start_date_key} AND {end_date_key}")
                except (ValueError, TypeError) as e:
                    print(f"Error parsing date filter: {e}")
                    continue
        
        # Build the final query
        query = """
        SELECT 
            processingdatekey as "ProcessingDateKey",
            commitmentamt as "CommitmentAmt",
            outstandingamt as "OutstandingAmt",
            bankid as "BankID"
        FROM analytics_data
        """
        
        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)
        
        query += " ORDER BY processingdatekey, bankid"
        
        return query
    
    def fetch_data(self, query: str) -> Optional[pl.DataFrame]:
        """Fetch data from database using the query"""
        try:
            print(f"📊 Executing query...")
            df = read_sql_polars(query, self.connection_uri)
            print(f"✅ Retrieved {len(df)} rows")
            return df
        except Exception as e:
            print(f"❌ Error fetching data: {e}")
            return None
    
    def run_analysis(self, df: pl.DataFrame) -> Optional[pl.DataFrame]:
        """Run the capped vs uncapped analysis"""
        try:
            print("🔄 Running setup_groups analysis...")
            ca_pivot, oa_pivot, deals_pivot = setup_groups(df)
            
            # Extract percentage differences
            ca_perc_diff = ca_pivot.get_column('perc_diff') if 'perc_diff' in ca_pivot.columns else None
            oa_perc_diff = oa_pivot.get_column('perc_diff') if 'perc_diff' in oa_pivot.columns else None
            deals_perc_diff = deals_pivot.get_column('perc_diff') if 'perc_diff' in deals_pivot.columns else None
            
            print("🔄 Running testCappedvsUncapped analysis...")
            result_df = testCappedvsUncapped(df, ca_perc_diff, oa_perc_diff, deals_perc_diff, None)
            
            print(f"✅ Analysis complete: {len(result_df)} rows")
            return result_df
        except Exception as e:
            print(f"❌ Error running analysis: {e}")
            return None
    
    def save_results(self, df: pl.DataFrame, template_name: str, filters: Dict[str, Any]) -> str:
        """Save results to CSV file"""
        try:
            # Create filename
            safe_name = template_name.replace(" ", "_").replace("/", "_")
            filename = f"{safe_name}_{self.timestamp}.csv"
            filepath = self.output_dir / filename
            
            # Add metadata columns
            df = df.with_columns([
                pl.lit(template_name).alias("template_name"),
                pl.lit(json.dumps(filters)).alias("filter_params"),
                pl.lit(self.timestamp).alias("run_timestamp")
            ])
            
            # Save to CSV
            df.write_csv(filepath)
            print(f"✅ Results saved to: {filepath}")
            
            # Also save metadata file
            metadata_file = self.output_dir / f"{safe_name}_{self.timestamp}_metadata.json"
            metadata = {
                "template_name": template_name,
                "filters": filters,
                "run_timestamp": self.timestamp,
                "row_count": len(df),
                "output_file": str(filename),
                "columns": df.columns
            }
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            print(f"📋 Metadata saved to: {metadata_file}")
            
            return str(filepath)
        except Exception as e:
            print(f"❌ Error saving results: {e}")
            return ""
    
    def process_template(self, template_key: str) -> bool:
        """Process a single template"""
        if template_key not in ANALYSIS_TEMPLATES:
            print(f"❌ Template '{template_key}' not found")
            return False
        
        template = ANALYSIS_TEMPLATES[template_key]
        print(f"\n{'='*60}")
        print(f"📦 Processing Template: {template['name']}")
        print(f"📝 Description: {template['description']}")
        print(f"🔧 Filters: {json.dumps(template['filters'], indent=2)}")
        print(f"{'='*60}")
        
        # Build and execute query
        query = self.build_query(template['filters'])
        print(f"\n📜 SQL Query:\n{query}\n")
        
        df = self.fetch_data(query)
        if df is None or len(df) == 0:
            print("⚠️ No data returned for this template")
            return False
        
        # Run analysis
        result_df = self.run_analysis(df)
        if result_df is None:
            return False
        
        # Save results
        output_path = self.save_results(result_df, template['name'], template['filters'])
        
        return bool(output_path)
    
    def process_custom(self, filters: Dict[str, Any], name: str = "Custom") -> bool:
        """Process custom filter parameters"""
        print(f"\n{'='*60}")
        print(f"📦 Processing Custom Analysis: {name}")
        print(f"🔧 Filters: {json.dumps(filters, indent=2)}")
        print(f"{'='*60}")
        
        # Build and execute query
        query = self.build_query(filters)
        print(f"\n📜 SQL Query:\n{query}\n")
        
        df = self.fetch_data(query)
        if df is None or len(df) == 0:
            print("⚠️ No data returned for these filters")
            return False
        
        # Run analysis
        result_df = self.run_analysis(df)
        if result_df is None:
            return False
        
        # Save results
        output_path = self.save_results(result_df, name, filters)
        
        return bool(output_path)
    
    def process_all_templates(self) -> Dict[str, bool]:
        """Process all defined templates"""
        results = {}
        for template_key in ANALYSIS_TEMPLATES:
            results[template_key] = self.process_template(template_key)
        return results
    
    def generate_summary_report(self, results: Dict[str, bool]) -> None:
        """Generate a summary report of all processed templates"""
        report_file = self.output_dir / f"pipeline_summary_{self.timestamp}.txt"
        
        with open(report_file, 'w') as f:
            f.write(f"Pipeline Processing Summary\n")
            f.write(f"{'='*60}\n")
            f.write(f"Timestamp: {self.timestamp}\n")
            f.write(f"Output Directory: {self.output_dir}\n\n")
            
            f.write(f"Templates Processed:\n")
            f.write(f"{'-'*40}\n")
            
            for template_key, success in results.items():
                template = ANALYSIS_TEMPLATES.get(template_key, {})
                status = "✅ SUCCESS" if success else "❌ FAILED"
                f.write(f"{status} - {template.get('name', template_key)}\n")
            
            success_count = sum(1 for s in results.values() if s)
            total_count = len(results)
            f.write(f"\n{'-'*40}\n")
            f.write(f"Total: {success_count}/{total_count} successful\n")
        
        print(f"\n📊 Summary report saved to: {report_file}")


def main():
    """Main entry point for the pipeline processor"""
    parser = argparse.ArgumentParser(description='Pipeline Processor for Volume Composites Analysis')
    
    # Add arguments
    parser.add_argument('--template', type=str, help='Template key to process (e.g., template1)')
    parser.add_argument('--all-templates', action='store_true', help='Process all templates')
    parser.add_argument('--custom', action='store_true', help='Use custom filters')
    parser.add_argument('--output-dir', type=str, default='pipeline_output', help='Output directory for CSV files')
    
    # Custom filter arguments
    parser.add_argument('--region', type=str, help='Region filter')
    parser.add_argument('--sba-filter', type=str, choices=['SBA', 'Non-SBA'], help='SBA classification')
    parser.add_argument('--lob-ids', nargs='+', help='Line of Business IDs')
    parser.add_argument('--commitment-sizes', nargs='+', help='Commitment size groups')
    parser.add_argument('--risk-groups', nargs='+', help='Risk group descriptions')
    parser.add_argument('--name', type=str, default='Custom', help='Name for custom analysis')
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = PipelineProcessor(output_dir=args.output_dir)
    
    # Connect to database
    if not processor.connect_database():
        sys.exit(1)
    
    # Process based on arguments
    if args.all_templates:
        print("🚀 Processing all templates...")
        results = processor.process_all_templates()
        processor.generate_summary_report(results)
        
    elif args.template:
        print(f"🚀 Processing template: {args.template}")
        success = processor.process_template(args.template)
        if not success:
            sys.exit(1)
            
    elif args.custom:
        print("🚀 Processing custom filters...")
        custom_filters = {
            "sba_classification": args.sba_filter,
            "region": args.region,
            "line_of_business_ids": args.lob_ids,
            "commitment_size_groups": args.commitment_sizes,
            "risk_group_descriptions": args.risk_groups
        }
        success = processor.process_custom(custom_filters, args.name)
        if not success:
            sys.exit(1)
            
    else:
        print("ℹ️ No action specified. Use --help for usage information.")
        print("\nAvailable templates:")
        for key, template in ANALYSIS_TEMPLATES.items():
            print(f"  {key}: {template['name']}")
        print("\nExamples:")
        print("  python pipeline_processor.py --template template1")
        print("  python pipeline_processor.py --all-templates")
        print("  python pipeline_processor.py --custom --region 'Rocky Mountain' --sba-filter Non-SBA")
    
    print("\n✨ Pipeline processing complete!")


if __name__ == "__main__":
    main()
