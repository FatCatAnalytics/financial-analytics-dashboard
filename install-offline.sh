#!/bin/bash

# Offline Installation Script for Financial Analytics Dashboard
# This script installs the application without internet access using bundled dependencies

echo "🚀 Financial Analytics Dashboard - Offline Installation"
echo "======================================================"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if offline dependencies exist
if [ ! -d "offline-deps" ]; then
    print_error "offline-deps directory not found!"
    echo "Please ensure you have the offline dependencies bundle."
    echo "Run the bundle-dependencies.sh script on a machine with internet access first."
    exit 1
fi

print_info "Found offline dependencies bundle"

# 1. Python Backend Setup
echo ""
echo "🐍 Setting up Python Backend..."
echo "--------------------------------"

# Check Python version
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
print_info "Found Python $PYTHON_VERSION"

# Create virtual environment
if [ ! -d ".venv" ]; then
    print_info "Creating Python virtual environment..."
    python3 -m venv .venv
    print_status "Virtual environment created"
else
    print_info "Virtual environment already exists"
fi

# Activate virtual environment and install from wheels
print_info "Installing Python dependencies from offline wheels..."
source .venv/bin/activate

# Install from local wheels
pip install --no-index --find-links offline-deps/python-wheels -r requirements.txt

if [ $? -eq 0 ]; then
    print_status "Python dependencies installed successfully"
else
    print_error "Failed to install Python dependencies"
    exit 1
fi

# 2. Node.js Frontend Setup
echo ""
echo "🎨 Setting up Node.js Frontend..."
echo "---------------------------------"

# Check Node.js version
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    print_error "Node.js version 18 or higher is required. Found version $NODE_VERSION"
    exit 1
fi

print_info "Found Node.js $(node --version)"

# Setup frontend dependencies
cd frontend

# Remove existing node_modules if it exists
if [ -d "node_modules" ]; then
    print_info "Removing existing node_modules..."
    rm -rf node_modules
fi

# Copy offline node_modules
print_info "Installing Node.js dependencies from offline bundle..."
cp -r ../offline-deps/node_modules .

if [ $? -eq 0 ]; then
    print_status "Node.js dependencies installed successfully"
else
    print_error "Failed to install Node.js dependencies"
    exit 1
fi

# Build the frontend for production (optional)
print_info "Building frontend for production..."
npm run build

if [ $? -eq 0 ]; then
    print_status "Frontend built successfully"
else
    print_warning "Frontend build failed, but development mode will still work"
fi

cd ..

# 3. Create startup scripts
echo ""
echo "📝 Creating startup scripts..."
echo "------------------------------"

# Create environment file template
if [ ! -f ".env" ]; then
    print_info "Creating .env template..."
    cat > .env << EOF
# Database Configuration (optional - will use CSV fallback if not set)
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=your_database
# DB_USER=your_username
# DB_PASSWORD=your_password

# SSL Configuration for development
NODE_TLS_REJECT_UNAUTHORIZED=0
PYTHONHTTPSVERIFY=0
EOF
    print_status ".env template created"
fi

# Make scripts executable
chmod +x start-dev.sh
chmod +x install-offline.sh

# 4. Verification
echo ""
echo "🔍 Verifying Installation..."
echo "----------------------------"

# Test Python imports
print_info "Testing Python dependencies..."
source .venv/bin/activate
python3 -c "
try:
    import fastapi, uvicorn, polars, pandas, numpy
    print('✅ All Python dependencies imported successfully')
except ImportError as e:
    print(f'❌ Python import error: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    print_error "Python dependency verification failed"
    exit 1
fi

# Test Node.js dependencies
print_info "Testing Node.js dependencies..."
cd frontend
if [ -d "node_modules/next" ] && [ -d "node_modules/react" ]; then
    print_status "Node.js dependencies verified"
else
    print_error "Node.js dependency verification failed"
    exit 1
fi
cd ..

# 5. Success message
echo ""
echo "🎉 Installation Complete!"
echo "========================"
echo ""
print_status "Financial Analytics Dashboard installed successfully!"
echo ""
echo "📋 Next Steps:"
echo "  1. Configure database (optional): Edit .env file"
echo "  2. Start the application: ./start-dev.sh"
echo "  3. Open browser to: http://localhost:3000"
echo ""
echo "📚 Documentation:"
echo "  - README.md - Setup and usage guide"
echo "  - SSL-TROUBLESHOOTING.md - SSL certificate issues"
echo ""
echo "🔗 URLs (after starting):"
echo "  - Dashboard: http://localhost:3000"
echo "  - API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo ""

# Display system info
echo "💻 System Information:"
echo "  - Python: $(python3 --version)"
echo "  - Node.js: $(node --version)"
echo "  - npm: $(npm --version)"
echo "  - OS: $(uname -s) $(uname -r)"
echo ""

print_status "Ready to run! Execute: ./start-dev.sh"
