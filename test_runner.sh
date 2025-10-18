#!/bin/bash

# Nextcloud Upload Daemon - Test Runner Script
# This script creates a Python virtual environment, installs dependencies including test frameworks,
# and runs the unit tests for the Nextcloud upload daemon.

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"
TEST_DIR="${SCRIPT_DIR}/tests"
REQUIREMENTS_FILE="${SCRIPT_DIR}/requirements.txt"

echo "Starting Nextcloud Upload Daemon test setup..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
else
    echo "Using existing virtual environment..."
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Check if pip is available in the virtual environment
if ! pip --version &> /dev/null; then
    echo "Error: pip is not available in the virtual environment."
    exit 1
fi

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install or upgrade dependencies
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r "$REQUIREMENTS_FILE"
else
    echo "Warning: requirements.txt not found. Installing minimal dependencies..."
    pip install watchdog requests
fi

# Install additional test dependencies
echo "Installing test dependencies..."
pip install coverage pytest pytest-cov

# Check if test directory exists
if [ ! -d "$TEST_DIR" ]; then
    echo "Error: Test directory not found: $TEST_DIR"
    exit 1
fi

echo "Setup completed successfully!"
echo ""

# Parse command line arguments
RUN_COVERAGE=false
VERBOSE=false
TEST_PATTERN="test_*.py"

while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage|-c)
            RUN_COVERAGE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --pattern|-p)
            TEST_PATTERN="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --coverage, -c    Run tests with coverage analysis"
            echo "  --verbose, -v     Run tests in verbose mode"
            echo "  --pattern, -p     Test file pattern (default: test_*.py)"
            echo "  --help, -h        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Run all tests"
            echo "  $0 --coverage         # Run tests with coverage"
            echo "  $0 --verbose          # Run tests in verbose mode"
            echo "  $0 -c -v             # Run tests with coverage and verbose output"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run tests
if [ "$RUN_COVERAGE" = true ]; then
    echo "Running tests with coverage analysis..."
    echo "========================================"
    
    if [ "$VERBOSE" = true ]; then
        python -m pytest "$TEST_DIR" --cov=nextcloud_upload_daemon --cov-report=term-missing --cov-report=html -v
    else
        python -m pytest "$TEST_DIR" --cov=nextcloud_upload_daemon --cov-report=term-missing --cov-report=html
    fi
    
    echo ""
    echo "Coverage report generated in htmlcov/ directory"
    echo "Open htmlcov/index.html in a web browser to view detailed coverage"
else
    echo "Running unit tests..."
    echo "===================="
    
    if [ "$VERBOSE" = true ]; then
        python -m unittest discover -s "$TEST_DIR" -p "$TEST_PATTERN" -v
    else
        python -m unittest discover -s "$TEST_DIR" -p "$TEST_PATTERN"
    fi
fi

# Check test results
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed successfully!"
else
    echo ""
    echo "❌ Some tests failed. Please check the output above."
    exit 1
fi

echo ""
echo "Test execution completed."