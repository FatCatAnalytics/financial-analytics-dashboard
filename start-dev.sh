#!/bin/bash

# Development startup script with SSL handling
# This script handles common SSL certificate issues on new machines

echo "🚀 Starting Financial Analytics Dashboard..."
echo ""

# Set environment variables for SSL handling
export NODE_TLS_REJECT_UNAUTHORIZED=0
export PYTHONHTTPSVERIFY=0
export SSL_VERIFY=false

echo "📋 Environment Setup:"
echo "  - NODE_TLS_REJECT_UNAUTHORIZED=0 (SSL verification disabled for dev)"
echo "  - PYTHONHTTPSVERIFY=0 (Python SSL verification disabled for dev)"
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please run:"
    echo "   python3 -m venv .venv"
    echo "   source .venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Check if node_modules exists
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

echo "🔧 Starting Backend (Port 8000)..."
source .venv/bin/activate
uvicorn api:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

echo "🎨 Starting Frontend (Port 3000)..."
cd frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Services Started:"
echo "  - Backend:  http://localhost:8000"
echo "  - Frontend: http://localhost:3000"
echo "  - API Docs: http://localhost:8000/docs"
echo ""
echo "🛑 To stop both services, press Ctrl+C"

# Function to cleanup background processes
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "✅ Services stopped"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Wait for user to press Ctrl+C
wait
