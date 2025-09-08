#!/bin/bash

# Download Offline Dependencies Bundle
# This script downloads the large offline dependencies from cloud storage

echo "📦 Downloading Financial Analytics Dashboard Dependencies..."
echo "========================================================="

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Bundle information
BUNDLE_SIZE="128MB"
BUNDLE_URL="https://example-cloud-storage.com/financial-dashboard-offline-deps.tar.gz"
BUNDLE_FILE="financial-dashboard-offline-deps.tar.gz"

print_info "Bundle size: $BUNDLE_SIZE"
print_info "This will download all offline dependencies for corporate deployment"
echo ""

# Check if bundle already exists
if [ -f "$BUNDLE_FILE" ]; then
    print_info "Bundle already exists. Remove it to re-download."
    exit 0
fi

# Download options
echo "📥 Available download methods:"
echo "1. Direct download (curl)"
echo "2. Google Drive"
echo "3. Dropbox"
echo "4. AWS S3"
echo "5. Azure Blob Storage"
echo ""

read -p "Choose download method (1-5): " method

case $method in
    1)
        print_info "Downloading via curl..."
        # curl -L -o "$BUNDLE_FILE" "$BUNDLE_URL"
        print_error "Direct URL not configured. Please set BUNDLE_URL in this script."
        ;;
    2)
        print_info "Google Drive download..."
        echo "Please download manually from:"
        echo "https://drive.google.com/file/d/YOUR_FILE_ID/view"
        ;;
    3)
        print_info "Dropbox download..."
        echo "Please download manually from:"
        echo "https://www.dropbox.com/s/YOUR_SHARE_LINK/financial-dashboard-offline-deps.tar.gz"
        ;;
    4)
        print_info "AWS S3 download..."
        echo "aws s3 cp s3://your-bucket/financial-dashboard-offline-deps.tar.gz ."
        ;;
    5)
        print_info "Azure Blob Storage download..."
        echo "az storage blob download --container-name your-container --name financial-dashboard-offline-deps.tar.gz --file ."
        ;;
    *)
        print_error "Invalid option"
        exit 1
        ;;
esac

# Verify download
if [ -f "$BUNDLE_FILE" ]; then
    print_success "Bundle downloaded successfully!"
    print_info "Extract with: tar -xzf $BUNDLE_FILE"
    print_info "Then run: ./install-offline.sh"
else
    print_info "Manual download required. After downloading:"
    echo "1. Place $BUNDLE_FILE in this directory"
    echo "2. Run: tar -xzf $BUNDLE_FILE"
    echo "3. Run: ./install-offline.sh"
fi
