# Volume Composites Pipeline Processor

## Overview
This pipeline processor runs the capped vs uncapped analysis with predefined or custom filter templates, outputting CSV files for use in compute engine pipelines.

## Quick Start

### Run a specific template:
```bash
./run_pipeline.sh 1  # Runs Template 1 (Non-SBA Rocky Mountain)
```

### Run all templates:
```bash
./run_pipeline.sh all
```

### Run with custom filters:
```bash
./run_pipeline.sh custom  # Interactive mode
```

## Available Templates

| Template | Name | Description |
|----------|------|-------------|
| template1 | Non-SBA Rocky Mountain | Non-SBA classification with Rocky Mountain region |
| template2 | Non-SBA High Quality | Non-SBA all regions with High Quality risk group |
| template3 | SBA All Regions | SBA classification across all regions |
| template4 | Large Commitments High Risk | Large commitment sizes with high risk groups |
| template5 | Southwest Non-SBA Medium Size | Southwest region Non-SBA with medium commitment sizes |
| template6 | Northeast High Quality SBA | Northeast region SBA with High Quality risk |
| template7 | Small Commitments All Regions | Small commitment sizes across all regions |
| template8 | Non-SBA Specific LOB | Non-SBA with specific Line of Business IDs |

## Direct Python Usage

### Run a specific template:
```bash
python pipeline_processor.py --template template1
```

### Run all templates:
```bash
python pipeline_processor.py --all-templates
```

### Custom analysis with specific filters:
```bash
python pipeline_processor.py --custom \
    --name "My Analysis" \
    --region "Rocky Mountain" \
    --sba-filter Non-SBA \
    --commitment-sizes "$1MM - $5MM" "$5MM - $10MM" \
    --risk-groups "High Quality"
```

## Output Files

All outputs are saved in the `pipeline_output/` directory:

- **CSV Files**: `{template_name}_{timestamp}.csv`
  - Contains analysis results with all calculated columns
  - Includes metadata columns (template_name, filter_params, run_timestamp)

- **Metadata Files**: `{template_name}_{timestamp}_metadata.json`
  - Contains filter parameters used
  - Includes row counts and column information
  - Timestamp of execution

- **Summary Report**: `pipeline_summary_{timestamp}.txt`
  - Generated when running all templates
  - Shows success/failure status for each template

## Filter Parameters

### SBA Classification
- `SBA`: Line of Business ID = '12'
- `Non-SBA`: Line of Business ID != '12'
- `null/None`: All classifications

### Region
- Specific region name (e.g., "Rocky Mountain", "Southwest", "Northeast")
- `null/None`: All regions

### Line of Business IDs
- List of specific IDs (e.g., ["1", "2", "3"])
- `null/None`: All IDs

### Commitment Size Groups
- Options: "< $250K", "$250K - $1MM", "$1MM - $5MM", "$5MM - $10MM", "$10MM - $25MM", "> $25MM"
- Can specify multiple as a list
- `null/None`: All sizes

### Risk Group Descriptions
- Options: "High Quality", "Pass", "Special Mention", "Substandard", "Doubtful", "Loss"
- Can specify multiple as a list
- `null/None`: All risk groups

## Integration with Compute Engine

### Automated Pipeline Execution
The script can be triggered automatically when the database is updated:

```bash
# Example cron job
0 2 * * * /path/to/Volume\ Composites/run_pipeline.sh all
```

### Google Cloud Compute Engine Setup
```bash
# Install on Compute Engine instance
git clone <repository>
cd "Volume Composites"
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with production database credentials

# Run pipeline
./run_pipeline.sh all
```

### Future Database Integration
The pipeline is designed to insert results back into the database:

```sql
-- Future target table structure
CREATE TABLE pipeline_results (
    id SERIAL PRIMARY KEY,
    template_name VARCHAR(255),
    run_timestamp TIMESTAMP,
    filter_params JSONB,
    processingdatekey BIGINT,
    commitmentamt DECIMAL(20,2),
    outstandingamt DECIMAL(20,2),
    deals INTEGER,
    ca_diff DECIMAL(10,6),
    oa_diff DECIMAL(10,6),
    deals_diff DECIMAL(10,6),
    ca_model_diff DECIMAL(10,6),
    oa_model_diff DECIMAL(10,6),
    deals_model_diff DECIMAL(10,6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Adding New Templates

Edit `pipeline_templates.json` or modify the `ANALYSIS_TEMPLATES` dictionary in `pipeline_processor.py`:

```python
"template9": {
    "name": "Your Template Name",
    "description": "Template description",
    "filters": {
        "sba_classification": "Non-SBA",
        "region": "Your Region",
        "line_of_business_ids": None,
        "commitment_size_groups": ["$1MM - $5MM"],
        "risk_group_descriptions": ["High Quality"]
    }
}
```

## Error Handling

- Database connection errors are logged and cause script to exit
- Empty result sets are handled gracefully with warnings
- All errors are logged with timestamps
- Failed templates don't stop processing of other templates (when using --all-templates)

## Performance Notes

- Each template typically processes in 1-5 seconds
- Large result sets (>100k rows) may take longer
- Database query performance depends on indexing
- Consider adding indexes on frequently filtered columns:
  ```sql
  CREATE INDEX idx_region ON analytics_data(region);
  CREATE INDEX idx_lineofbusinessid ON analytics_data(lineofbusinessid);
  CREATE INDEX idx_commitmentsizegroup ON analytics_data(commitmentsizegroup);
  CREATE INDEX idx_riskgroupdesc ON analytics_data(riskgroupdesc);
  ```

## Monitoring

Check the pipeline output directory for:
- Latest run timestamps
- File sizes (indicator of data volume)
- Metadata files for filter verification
- Summary reports for batch run status

## Support

For issues or questions:
1. Check the error messages in the console output
2. Review the metadata files for filter parameters
3. Verify database connectivity with `python main.py`
4. Check the `.env` file for correct credentials
