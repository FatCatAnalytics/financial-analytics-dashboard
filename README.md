# Volume Composites Dashboard

A full-stack financial analytics dashboard that connects React frontend to PostgreSQL database via FastAPI backend.

## Architecture

```
Frontend (React/TypeScript) ←→ Backend (FastAPI/Python) ←→ PostgreSQL Database
     ↓                              ↓                           ↓
- Modern UI with Tailwind     - REST API endpoints        - Sample CSV data
- Real-time data display      - Database connectivity     - Aggregated views
- Interactive filtering       - Data processing           - Performance indexes
```

## Quick Start

### Prerequisites

- **PostgreSQL** (version 12+)
- **Python** (version 3.8+)
- **Node.js** (version 16+)
- **npm** or **yarn**

### 1. Start PostgreSQL

**macOS:**
```bash
brew services start postgresql
```

**Ubuntu/Linux:**
```bash
sudo systemctl start postgresql
```

**Windows:**
Start PostgreSQL service from the Services panel

### 2. Run the Setup Script

```bash
# From the project root directory
python start_services.py
```

This script will:
- ✅ Check PostgreSQL connection
- ✅ Create `.env` configuration file
- ✅ Install Python dependencies
- ✅ Set up database and import sample.csv data
- ✅ Start the FastAPI backend server

### 3. Start the Frontend

In a new terminal:

```bash
cd frontend
npm install
npm run dev
```

### 4. Access the Dashboard

Open your browser to: **http://localhost:5173**

## Manual Setup (Alternative)

If you prefer to set up manually:

### Backend Setup

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment:**
Create `.env` file:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=volume_composites
DB_USER=postgres
DB_PASSWORD=your_password
API_PORT=8000
```

3. **Set up database:**
```bash
python setup_database.py
```

4. **Start backend:**
```bash
python backend_api.py
```

### Frontend Setup

1. **Install dependencies:**
```bash
cd frontend
npm install
```

2. **Start development server:**
```bash
npm run dev
```

## Database Schema

The application uses a PostgreSQL database with the following structure:

### Main Table: `analytics_data`
- **ProcessingDateKey**: Date in YYYYMMDD format
- **CommitmentAmt**: Loan commitment amount
- **OutstandingAmt**: Outstanding amount
- **Region**: Geographic region
- **LineofBusinessId**: Business line identifier
- **CommitmentSizeGroup**: Size category
- **RiskGroupDesc**: Risk classification
- **BankID**: Bank identifier
- Plus additional fields from sample.csv

### Aggregated View: `aggregated_analytics`
- Monthly summaries with period-over-period calculations
- Automatically calculated differences (ca_diff, oa_diff, deals_diff)
- Optimized for dashboard queries

## API Endpoints

### Connection & Health
- `GET /health` - Health check
- `GET /api/connection-status` - Database connection status

### Data Endpoints
- `GET /api/filter-options` - Available filter values
- `POST /api/query` - Execute filtered queries
- `GET /api/analytics-data` - Time series analytics data
- `GET /api/summary-stats` - Summary statistics

### Example API Usage

**Get filter options:**
```bash
curl http://localhost:8000/api/filter-options
```

**Execute filtered query:**
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "filters": {
      "region": ["Southeast", "Northeast"],
      "lineOfBusiness": ["1 - Commercial Banking"]
    },
    "limit": 100
  }'
```

## Features

### Frontend Features
- 📊 **Interactive Dashboard** - Real-time data visualization
- 🔍 **Advanced Filtering** - Multiple filter types with custom ranges
- 📈 **Charts & Tables** - Multiple data visualization modes
- 🔗 **Live Connection Status** - Real-time database connection monitoring
- 📱 **Responsive Design** - Works on desktop and mobile

### Backend Features
- 🚀 **FastAPI** - High-performance async API
- 🔒 **CORS Enabled** - Secure cross-origin requests
- 📊 **PostgreSQL Integration** - Optimized database queries
- 🛡️ **Error Handling** - Comprehensive error management
- 📈 **Performance Optimized** - Indexed queries and efficient data processing

### Database Features
- 🗄️ **PostgreSQL** - Reliable, scalable database
- 📊 **Aggregated Views** - Pre-calculated analytics
- 🔍 **Indexed Queries** - Fast filtering and searching
- 📈 **Time Series Data** - Historical trend analysis

## Data Flow

1. **Sample CSV** → PostgreSQL database (via setup_database.py)
2. **Frontend filters** → API request (via api.ts service)
3. **API processes** → Database query (via backend_api.py)
4. **Database returns** → Processed data (via PostgreSQL views)
5. **API responds** → Frontend updates (via React state)

## Troubleshooting

### Database Connection Issues

**Error: "Connection failed"**
- Check if PostgreSQL is running
- Verify credentials in `.env` file
- Test connection: `psql -h localhost -p 5432 -U postgres`

### Backend Issues

**Error: "Port already in use"**
- Kill existing process: `pkill -f backend_api.py`
- Change port in `.env`: `API_PORT=8001`

**Error: "Module not found"**
- Install dependencies: `pip install -r requirements.txt`

### Frontend Issues

**Error: "Cannot connect to backend"**
- Ensure backend is running on http://localhost:8000
- Check CORS configuration in backend_api.py
- Verify API_URL in frontend environment

### Data Issues

**Error: "No data returned"**
- Check if sample.csv was imported: `python setup_database.py`
- Verify data exists: Query `SELECT COUNT(*) FROM analytics_data;`

## Development

### Adding New Features

1. **Backend**: Add endpoints in `backend_api.py`
2. **Frontend**: Add API calls in `src/services/api.ts`
3. **Database**: Modify schema in `setup_database.py`

### Environment Variables

**Backend (.env):**
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=volume_composites
DB_USER=postgres
DB_PASSWORD=password
API_PORT=8000
```

**Frontend:**
```env
VITE_API_URL=http://localhost:8000
```

## Production Deployment

### Backend Deployment
- Use production PostgreSQL instance
- Set secure environment variables
- Use production WSGI server (gunicorn)
- Enable SSL/HTTPS

### Frontend Deployment
- Build for production: `npm run build`
- Deploy static files to CDN/web server
- Update API_URL for production backend

### Database Deployment
- Use managed PostgreSQL service
- Set up proper backup strategy
- Configure connection pooling
- Monitor performance metrics

## Support

For issues and questions:
1. Check this README for common solutions
2. Review the error logs in terminal
3. Verify all prerequisites are installed
4. Test individual components (database → backend → frontend)

## License

This project is for internal use and development purposes.
