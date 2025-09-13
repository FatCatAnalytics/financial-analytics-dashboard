#!/usr/bin/env python3
"""
Startup script for Volume Composites Dashboard
This script will:
1. Set up the PostgreSQL database
2. Start the backend API server
3. Provide instructions for starting the frontend
"""

import subprocess
import sys
import os
import time
import webbrowser
from pathlib import Path

def run_command(command, description, check=True, background=False):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    
    try:
        if background:
            # Run in background
            subprocess.Popen(command, shell=True)
            time.sleep(2)  # Give it time to start
            print(f"✅ {description} started in background")
        else:
            result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ {description} completed successfully")
                if result.stdout:
                    print(f"   Output: {result.stdout.strip()}")
            else:
                print(f"❌ {description} failed")
                if result.stderr:
                    print(f"   Error: {result.stderr.strip()}")
                return False
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during {description}: {e}")
        return False
    
    return True

def check_postgresql():
    """Check if PostgreSQL is running"""
    print("🔍 Checking PostgreSQL status...")
    
    # Try to connect to PostgreSQL
    result = subprocess.run(
        "psql -h localhost -p 5432 -U postgres -d postgres -c 'SELECT 1;'",
        shell=True,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ PostgreSQL is running")
        return True
    else:
        print("❌ PostgreSQL is not running or not accessible")
        print("\n📝 To start PostgreSQL:")
        print("  macOS: brew services start postgresql")
        print("  Ubuntu: sudo systemctl start postgresql")
        print("  Windows: Start PostgreSQL service from Services panel")
        return False

def setup_environment():
    """Set up environment variables"""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("📝 Creating .env file...")
        with open(env_file, 'w') as f:
            f.write("""# PostgreSQL Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=volume_composites
DB_USER=postgres
DB_PASSWORD=password

# Application Configuration
API_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
""")
        print("✅ Created .env file with default configuration")
        print("   📝 Please update the DB_PASSWORD in .env file if needed")
    else:
        print("✅ .env file already exists")

def install_dependencies():
    """Install Python dependencies"""
    if not Path("requirements.txt").exists():
        print("❌ requirements.txt not found")
        return False
    
    return run_command(
        f"{sys.executable} -m pip install -r requirements.txt",
        "Installing Python dependencies"
    )

def setup_database():
    """Set up the PostgreSQL database"""
    return run_command(
        f"{sys.executable} setup_database.py",
        "Setting up PostgreSQL database and importing sample data"
    )

def start_backend():
    """Start the FastAPI backend server"""
    print("🚀 Starting backend API server...")
    
    # Start the backend in background
    backend_process = subprocess.Popen([
        sys.executable, "backend_api.py"
    ])
    
    # Give it time to start
    time.sleep(3)
    
    # Check if it's running
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend API server is running at http://localhost:8000")
            return backend_process
        else:
            print("❌ Backend API server is not responding correctly")
            return None
    except Exception as e:
        print(f"❌ Failed to verify backend server: {e}")
        return None

def main():
    """Main startup sequence"""
    print("🚀 Volume Composites Dashboard Startup")
    print("="*50)
    
    # Check current directory
    if not Path("sample.csv").exists():
        print("❌ Please run this script from the project root directory")
        print("   (where sample.csv is located)")
        return False
    
    # Step 1: Check PostgreSQL
    if not check_postgresql():
        print("\n❌ PostgreSQL is required. Please start PostgreSQL and try again.")
        return False
    
    # Step 2: Set up environment
    setup_environment()
    
    # Step 3: Install dependencies
    if not install_dependencies():
        return False
    
    # Step 4: Set up database
    if not setup_database():
        print("\n❌ Database setup failed. Please check PostgreSQL connection and try again.")
        return False
    
    # Step 5: Start backend
    backend_process = start_backend()
    if not backend_process:
        return False
    
    # Step 6: Instructions for frontend
    print("\n" + "="*50)
    print("🎉 Backend is running successfully!")
    print("\n📋 Next steps:")
    print("1. Open a new terminal window")
    print("2. Navigate to the frontend directory:")
    print("   cd frontend")
    print("3. Install frontend dependencies (if not already done):")
    print("   npm install")
    print("4. Start the frontend development server:")
    print("   npm run dev")
    print("5. Open your browser to http://localhost:5173")
    
    print("\n🔗 API Endpoints:")
    print("   Health Check: http://localhost:8000/health")
    print("   Filter Options: http://localhost:8000/api/filter-options")
    print("   Analytics Data: http://localhost:8000/api/analytics-data")
    
    print("\n⚡ The backend will continue running in the background.")
    print("   Press Ctrl+C to stop the backend server.")
    
    try:
        # Keep the script running to maintain the backend process
        backend_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down backend server...")
        backend_process.terminate()
        backend_process.wait()
        print("✅ Backend server stopped")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
