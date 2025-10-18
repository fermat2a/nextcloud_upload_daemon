#!/bin/bash

# Nextcloud Upload Daemon - Startup Script
# This script creates a Python virtual environment, installs dependencies,
# and starts the Nextcloud upload daemon.

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"
PYTHON_SCRIPT="${SCRIPT_DIR}/nextcloud_upload_daemon.py"
REQUIREMENTS_FILE="${SCRIPT_DIR}/requirements.txt"

echo "Starting Nextcloud Upload Daemon setup..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Check if pip is installed
if ! python3 -m pip --version &> /dev/null; then
    echo "Error: pip is not installed. Please install pip first."
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

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: Python script not found: $PYTHON_SCRIPT"
    exit 1
fi

echo "Setup completed successfully!"
echo "Starting Nextcloud Upload Daemon..."

# Start the daemon with any arguments passed to this script
python3 "$PYTHON_SCRIPT" "$@"