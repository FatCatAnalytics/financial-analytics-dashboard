#!/bin/bash

# Pipeline Runner Script for Volume Composites Analysis
# This script provides easy access to common pipeline operations

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

# Function to show usage
show_usage() {
    echo "Volume Composites Pipeline Runner"
    echo "================================="
    echo ""
    echo "Usage: ./run_pipeline.sh [OPTION]"
    echo ""
    echo "Options:"
    echo "  1  - Run Template 1 (Non-SBA Rocky Mountain)"
    echo "  2  - Run Template 2 (Non-SBA High Quality)"
    echo "  3  - Run Template 3 (SBA All Regions)"
    echo "  4  - Run Template 4 (Large Commitments High Risk)"
    echo "  5  - Run Template 5 (Southwest Non-SBA Medium Size)"
    echo "  6  - Run Template 6 (Northeast High Quality SBA)"
    echo "  7  - Run Template 7 (Small Commitments All Regions)"
    echo "  8  - Run Template 8 (Non-SBA Specific LOB)"
    echo "  all - Run all templates"
    echo "  custom - Run with custom parameters"
    echo "  help - Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./run_pipeline.sh 1        # Run template 1"
    echo "  ./run_pipeline.sh all      # Run all templates"
    echo "  ./run_pipeline.sh custom   # Interactive custom run"
}

# Function to run a specific template
run_template() {
    template_num=$1
    print_color "$BLUE" "🚀 Running Template $template_num..."
    python pipeline_processor.py --template "template$template_num"
    
    if [ $? -eq 0 ]; then
        print_color "$GREEN" "✅ Template $template_num completed successfully!"
    else
        print_color "$RED" "❌ Template $template_num failed!"
        exit 1
    fi
}

# Function to run all templates
run_all_templates() {
    print_color "$BLUE" "🚀 Running all templates..."
    python pipeline_processor.py --all-templates
    
    if [ $? -eq 0 ]; then
        print_color "$GREEN" "✅ All templates completed successfully!"
    else
        print_color "$RED" "❌ Some templates failed!"
        exit 1
    fi
}

# Function to run custom analysis
run_custom() {
    print_color "$YELLOW" "📝 Custom Analysis Configuration"
    echo ""
    
    # Get custom parameters
    read -p "Enter analysis name (default: Custom): " name
    name=${name:-Custom}
    
    echo "Select SBA Classification:"
    echo "  1) SBA"
    echo "  2) Non-SBA"
    echo "  3) All (no filter)"
    read -p "Choice (1-3): " sba_choice
    
    case $sba_choice in
        1) sba_filter="--sba-filter SBA";;
        2) sba_filter="--sba-filter Non-SBA";;
        *) sba_filter="";;
    esac
    
    read -p "Enter region (or press Enter for all): " region
    if [ ! -z "$region" ]; then
        region_filter="--region \"$region\""
    else
        region_filter=""
    fi
    
    read -p "Enter Line of Business IDs (space-separated, or press Enter for all): " lob_ids
    if [ ! -z "$lob_ids" ]; then
        lob_filter="--lob-ids $lob_ids"
    else
        lob_filter=""
    fi
    
    read -p "Enter Commitment Size Groups (space-separated, or press Enter for all): " sizes
    if [ ! -z "$sizes" ]; then
        size_filter="--commitment-sizes $sizes"
    else
        size_filter=""
    fi
    
    read -p "Enter Risk Group Descriptions (space-separated, or press Enter for all): " risks
    if [ ! -z "$risks" ]; then
        risk_filter="--risk-groups $risks"
    else
        risk_filter=""
    fi
    
    # Build and run command
    cmd="python pipeline_processor.py --custom --name \"$name\" $sba_filter $region_filter $lob_filter $size_filter $risk_filter"
    
    print_color "$BLUE" "🚀 Running custom analysis..."
    echo "Command: $cmd"
    eval $cmd
    
    if [ $? -eq 0 ]; then
        print_color "$GREEN" "✅ Custom analysis completed successfully!"
    else
        print_color "$RED" "❌ Custom analysis failed!"
        exit 1
    fi
}

# Check Python environment
check_environment() {
    print_color "$BLUE" "🔍 Checking environment..."
    
    # Check if Python is available
    if ! command -v python &> /dev/null; then
        print_color "$RED" "❌ Python is not installed or not in PATH"
        exit 1
    fi
    
    # Check if required packages are installed
    python -c "import pandas, polars, psycopg2, dotenv" 2>/dev/null
    if [ $? -ne 0 ]; then
        print_color "$YELLOW" "⚠️ Some required packages are missing"
        read -p "Install required packages? (y/n): " install_choice
        if [ "$install_choice" = "y" ]; then
            pip install -r requirements.txt
        else
            exit 1
        fi
    fi
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        print_color "$RED" "❌ .env file not found"
        print_color "$YELLOW" "Please create .env file with database credentials"
        exit 1
    fi
    
    print_color "$GREEN" "✅ Environment check passed"
}

# Main script logic
main() {
    # Check environment first
    check_environment
    
    # Create output directory if it doesn't exist
    mkdir -p pipeline_output
    
    # Parse command line arguments
    case "$1" in
        1|2|3|4|5|6|7|8)
            run_template "$1"
            ;;
        all)
            run_all_templates
            ;;
        custom)
            run_custom
            ;;
        help|--help|-h)
            show_usage
            ;;
        "")
            print_color "$YELLOW" "No option specified. Showing available templates:"
            echo ""
            python pipeline_processor.py
            echo ""
            echo "Run './run_pipeline.sh help' for usage information"
            ;;
        *)
            print_color "$RED" "Invalid option: $1"
            echo ""
            show_usage
            exit 1
            ;;
    esac
    
    # Show output location
    echo ""
    print_color "$BLUE" "📁 Output files are in: pipeline_output/"
    ls -la pipeline_output/*.csv 2>/dev/null | tail -5
}

# Run main function
main "$@"
