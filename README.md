# Financial Analytics Dashboard

A comprehensive financial analytics dashboard with capped vs uncapped composite analysis, built with Python backend and React frontend.

## Features

- **Real-time Database Integration**: PostgreSQL database with CSV fallback
- **Advanced Filtering**: Multi-dimensional filtering across regions, business lines, risk groups
- **Capped Analysis**: Integrated `testCappedvsUncapped` function for sophisticated composite analysis
- **Professional Visualizations**: 6 different chart views with interactive data
- **Modern UI**: Built with Next.js, TypeScript, Tailwind CSS, and Figma components

## Architecture

### Backend (Python/FastAPI)
- **`main.py`**: Core data processing and composite analysis logic
- **`api.py`**: FastAPI REST API with PostgreSQL and CSV endpoints
- **`data_processor.py`**: CSV data processing and transformation utilities

### Frontend (Next.js/React)
- **Dashboard**: Main analytics dashboard with status cards and filter panel
- **Data View**: Rich data table with percentage badges and analysis results
- **Charts**: 6-tab visualization (Time Series, Benchmark, Individual, Actual vs Model, Differences, Overview)
- **Analysis**: Dedicated capped vs uncapped analysis interface

## Quick Start

### 1. Backend Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Start API server
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 3. Database Configuration (Optional)
Create `.env` file for PostgreSQL connection:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database
DB_USER=your_username
DB_PASSWORD=your_password
```

## API Endpoints

- **`GET /health`**: Health check
- **`GET /db/status`**: Database connection status
- **`GET /filters`**: Available filter options (database or CSV fallback)
- **`POST /data`**: Filtered analytics data (database or CSV fallback)
- **`POST /composites`**: Composite analysis results
- **`POST /analysis/capped-vs-uncapped`**: Run testCappedvsUncapped function

## Data Flow

```
PostgreSQL Database (Primary) → API Endpoints → React Dashboard
        ↓ (fallback)
CSV Data (test-2.csv) → Processed Data → Charts & Tables
```

## URLs

- **Frontend Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Pages

- **`/`**: Main dashboard with status and filter panel
- **`/filters`**: Advanced filtering interface
- **`/data`**: Data table with capped analysis results
- **`/composites`**: Chart visualizations with all analysis tabs
- **`/analysis`**: Direct access to capped vs uncapped analysis

## Technologies

**Backend**: Python, FastAPI, Polars, Pandas, PostgreSQL, psycopg2
**Frontend**: Next.js, TypeScript, Tailwind CSS, Recharts, Radix UI
**Data**: PostgreSQL database with CSV fallback support
