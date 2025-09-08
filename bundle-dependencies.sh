#!/bin/bash

# Dependency Bundling Script for Financial Analytics Dashboard
# Run this script on a machine with internet access to create offline installation bundle

echo "📦 Financial Analytics Dashboard - Dependency Bundling"
echo "====================================================="
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

# Create offline-deps directory
print_info "Creating offline-deps directory structure..."
mkdir -p offline-deps/python-wheels
mkdir -p offline-deps/node_modules
print_status "Directory structure created"

# 1. Bundle Python Dependencies
echo ""
echo "🐍 Bundling Python Dependencies..."
echo "----------------------------------"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    print_info "Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies first (to ensure we have them)
print_info "Installing Python dependencies..."
pip install -r requirements.txt

# Download all wheels
print_info "Downloading Python wheel files..."
pip download -r requirements.txt -d offline-deps/python-wheels

if [ $? -eq 0 ]; then
    print_status "Python wheels downloaded successfully"
    WHEEL_COUNT=$(ls -1 offline-deps/python-wheels/*.whl | wc -l)
    print_info "Downloaded $WHEEL_COUNT wheel files"
else
    print_error "Failed to download Python wheels"
    exit 1
fi

# 2. Bundle Node.js Dependencies
echo ""
echo "🎨 Bundling Node.js Dependencies..."
echo "----------------------------------"

cd frontend

# Install dependencies if not already installed
if [ ! -d "node_modules" ]; then
    print_info "Installing Node.js dependencies..."
    npm install
fi

# Copy node_modules to offline bundle
print_info "Copying Node.js modules to offline bundle..."
cp -r node_modules ../offline-deps/

if [ $? -eq 0 ]; then
    print_status "Node.js modules bundled successfully"
    MODULE_COUNT=$(find ../offline-deps/node_modules -name "package.json" | wc -l)
    print_info "Bundled $MODULE_COUNT Node.js packages"
else
    print_error "Failed to bundle Node.js modules"
    exit 1
fi

cd ..

# 3. Create bundle information
echo ""
echo "📋 Creating Bundle Information..."
echo "--------------------------------"

# Create bundle info file
cat > offline-deps/BUNDLE_INFO.md << EOF
# Offline Dependencies Bundle

Generated on: $(date)
System: $(uname -s) $(uname -r)
Python: $(python3 --version)
Node.js: $(node --version)
npm: $(npm --version)

## Contents

### Python Wheels ($(ls -1 offline-deps/python-wheels/*.whl | wc -l) packages)
\`\`\`
$(ls -1 offline-deps/python-wheels/*.whl | xargs -n 1 basename)
\`\`\`

### Node.js Modules ($(find offline-deps/node_modules -name "package.json" | wc -l) packages)
Located in: offline-deps/node_modules/

## Installation Instructions

1. Copy the entire 'offline-deps' directory to your target machine
2. Run: ./install-offline.sh
3. Start application: ./start-dev.sh

## Bundle Size
- Python wheels: $(du -sh offline-deps/python-wheels | cut -f1)
- Node.js modules: $(du -sh offline-deps/node_modules | cut -f1)
- Total size: $(du -sh offline-deps | cut -f1)

## Compatibility
This bundle was created for:
- macOS/Linux systems
- Python 3.8+
- Node.js 18+

For Windows systems, you may need to regenerate Python wheels for Windows.
EOF

print_status "Bundle information created"

# 4. Create portable archive (optional)
echo ""
echo "📦 Creating Portable Archive..."
echo "------------------------------"

print_info "Creating compressed archive of offline dependencies..."
tar -czf financial-dashboard-offline-deps.tar.gz offline-deps/

if [ $? -eq 0 ]; then
    ARCHIVE_SIZE=$(du -sh financial-dashboard-offline-deps.tar.gz | cut -f1)
    print_status "Archive created: financial-dashboard-offline-deps.tar.gz ($ARCHIVE_SIZE)"
else
    print_warning "Failed to create archive, but offline-deps directory is ready"
fi

# 5. Display summary
echo ""
echo "🎉 Bundling Complete!"
echo "===================="
echo ""
print_status "All dependencies bundled successfully!"
echo ""
echo "📊 Bundle Summary:"
echo "  - Python wheels: $(ls -1 offline-deps/python-wheels/*.whl | wc -l) packages"
echo "  - Node.js modules: $(find offline-deps/node_modules -name "package.json" | wc -l) packages"
echo "  - Total size: $(du -sh offline-deps | cut -f1)"
if [ -f "financial-dashboard-offline-deps.tar.gz" ]; then
    echo "  - Archive size: $(du -sh financial-dashboard-offline-deps.tar.gz | cut -f1)"
fi
echo ""
echo "📋 Files Created:"
echo "  - offline-deps/ (directory with all dependencies)"
echo "  - offline-deps/BUNDLE_INFO.md (bundle information)"
if [ -f "financial-dashboard-offline-deps.tar.gz" ]; then
    echo "  - financial-dashboard-offline-deps.tar.gz (portable archive)"
fi
echo ""
echo "🚀 Usage:"
echo "  1. Copy offline-deps/ directory to target machine"
echo "  2. Run: ./install-offline.sh on target machine"
echo "  3. Start: ./start-dev.sh"
echo ""
print_status "Ready for offline deployment!"
