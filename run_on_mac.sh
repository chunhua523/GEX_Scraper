#!/bin/bash

# Ensure we are in the script's directory
cd "$(dirname "$0")"

echo "========================================"
echo "      Lieta Scraper Auto-Updater"
echo "========================================"

# Check for internet connection (simple ping)
echo "Checking internet connection..."
if ping -c 1 github.com &> /dev/null; then
    echo "Internet connected. Checking for updates..."
    # Attempt to pull latest changes
    git pull origin main
    if [ $? -eq 0 ]; then
        echo "Update check complete."
    else
        echo "Update failed. Proceeding with existing version."
    fi
else
    echo "No internet connection. Skipping update."
fi

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    echo "Please install Python 3 from https://www.python.org/downloads/"
    echo "Press any key to exit..."
    read -n 1
    exit 1
fi

# Virtual Environment Setup
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment (.venv)..."
    python3 -m venv .venv
fi

# Activate Virtual Environment
source .venv/bin/activate

# Install/Update Dependencies
echo "Checking dependencies..."
pip install -r requirements.txt

# Install Playwright Browsers
echo "Verifying browser binaries..."
playwright install chromium

# Run Application
echo "Starting Lieta Scraper..."
python main.py
