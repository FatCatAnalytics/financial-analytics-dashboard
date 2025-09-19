# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a full-stack financial analytics dashboard for volume composites analysis. The system processes loan commitment data through multiple architectures:

1. **Interactive Dashboard**: React/TypeScript frontend + FastAPI backend + PostgreSQL database
2. **Pipeline Processor**: Batch analysis system that generates CSV outputs for compute engine workflows
3. **Database Analytics**: PostgreSQL-based data warehouse with pre-aggregated views

## Common Development Commands

### Full Stack Development

**Quick start (automated setup):**
```bash
python start_services.py
```
This will set up PostgreSQL database, start backend API, and provide frontend setup instructions.

**Manual backend setup:**
```bash
pip install -r requirements.txt
python setup_database.py    # Creates database schema and imports sample.csv
python backend_api.py       # Starts FastAPI server on port 8000
```

**Frontend development:**
```bash
cd frontend
npm install
npm run dev                 # Starts Vite dev server on port 5173
```

### Testing and Validation

**Test database connection:**
```bash
python main.py              # Tests connection and shows data statistics
```

**Backend API health check:**
```bash
curl http://localhost:8000/health
```

**Run specific tests:**
```bash
pytest                      # Runs all tests (if test files exist)
```

### Pipeline Processing

**Run single analysis template:**
```bash
./run_pipeline.sh 1         # Runs Template 1 (Non-SBA Rocky Mountain)
python pipeline_processor.py --template template1
```

**Run all analysis templates:**
```bash
./run_pipeline.sh all
python pipeline_processor.py --all-templates
```

**Custom analysis with filters:**
```bash
python pipeline_processor.py --custom --region "Rocky Mountain" --sba-filter "Non-SBA" --name "My Analysis"
```

### Database Operations

**Reset database:**
```bash
python setup_database.py   # Recreates tables and reimports data
```

**Direct database access:**
```bash
psql -h localhost -p 5432 -U postgres -d volume_composites
```

### Build and Deployment

**Frontend production build:**
```bash
cd frontend
npm run build               # Creates optimized build in dist/
```

**Backend production:**
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend_api:app
```

## Architecture Overview

### Data Flow Architecture

1. **Raw Data**: `sample.csv` (tab-separated) contains loan commitment data
2. **Database Layer**: PostgreSQL with `analytics_data` table and `aggregated_analytics` view
3. **API Layer**: FastAPI provides REST endpoints for frontend and external integrations
4. **Frontend**: React/TypeScript SPA with real-time data visualization
5. **Pipeline**: Batch processor for capped vs uncapped analysis with templated filters

### Key Database Schema

**Main Table: `analytics_data`**
- ProcessingDateKey (BIGINT, YYYYMMDD format)
- CommitmentAmt, OutstandingAmt (DECIMAL)
- Region, LineofBusinessId, CommitmentSizeGroup, RiskGroupDesc
- Indexed on: ProcessingDateKey, Region, LineofBusinessId, BankID

**Aggregated View: `aggregated_analytics`**
- Pre-calculated monthly summaries with period-over-period differences
- Fields: ca_diff, oa_diff, deals_diff (percentage changes)
- Used for dashboard time series visualization

### Component Structure

**Backend (Python/FastAPI)**
- `backend_api.py`: Main API server with CORS, health checks, and data endpoints
- `main.py`: Core database connectivity and analysis functions
- `setup_database.py`: Database schema creation and data import
- `pipeline_processor.py`: Batch analysis with templated filters

**Frontend (React/TypeScript)**
- Built with Vite, Tailwind CSS, and Radix UI components
- `src/services/api.ts`: Backend API integration (expected location)
- Recharts for data visualization
- Real-time connection status monitoring

**Pipeline System**
- `run_pipeline.sh`: Shell script wrapper for common pipeline operations
- `pipeline_templates.json`: Predefined filter combinations for analysis
- Output directory: `pipeline_output/` with CSV and metadata files

## Configuration

### Environment Variables

**Backend (.env):**
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=volume_composites
DB_USER=postgres
DB_PASSWORD=your_password
API_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

**Frontend:**
```env
VITE_API_URL=http://localhost:8000
```

### Database Connection

The system supports both direct psycopg2 connections and SQLAlchemy URI connections. Connection pooling and SSL are configured for production use.

## Analysis Templates

The pipeline processor includes 8 predefined analysis templates:

1. **Template 1**: Non-SBA Rocky Mountain region analysis
2. **Template 2**: Non-SBA all regions with High Quality risk
3. **Template 3**: SBA classification across all regions
4. **Template 4**: Large commitments with high risk groups
5. **Template 5**: Southwest Non-SBA medium commitment sizes
6. **Template 6**: Northeast High Quality SBA analysis
7. **Template 7**: Small commitments across all regions
8. **Template 8**: Non-SBA specific Line of Business analysis

Each template outputs CSV files with calculated difference metrics (ca_diff, oa_diff, deals_diff) for period-over-period analysis.

## Key Integration Points

### API Endpoints Structure
- `/health`: System health and database connectivity
- `/api/connection-status`: Real-time database status for frontend
- `/api/filter-options`: Dynamic filter values from database
- `/api/query`: Filtered data queries with flexible parameters
- `/api/analytics-data`: Time series data for charts

### Filter System Architecture
The system supports complex filtering across multiple dimensions:
- SBA Classification (SBA/Non-SBA based on LineofBusinessId = '12')
- Geographic regions
- Commitment size groups
- Risk group descriptions
- Date ranges with multiple operators
- Custom commitment amount ranges

### Data Processing Pipeline
1. Raw CSV import with data cleaning and type conversion
2. PostgreSQL storage with performance indexes
3. Aggregated view creation for dashboard queries
4. Template-based analysis for batch processing
5. CSV export for external compute engines

## Development Notes

- The system handles both capped and uncapped analysis workflows
- Database queries are optimized with indexes on frequently filtered columns
- Frontend uses Axios for API communication with automatic error handling
- Pipeline outputs include metadata files for audit trails
- Connection handling includes keepalive settings for long-running queries
- All numeric calculations handle NULL values and edge cases appropriately

<citations>
<document>
    <document_type>WARP_DOCUMENTATION</document_type>
    <document_id>getting-started/quickstart-guide/coding-in-warp</document_id>
</document>
</citations>