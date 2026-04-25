#!/bin/bash

# Ensure we are in the script's directory
cd "$(dirname "$0")"

echo "========================================"
echo "      Lieta Scraper Auto-Updater"
echo "========================================"

# Check for internet connection
echo "Checking internet connection..."
if ping -c 1 github.com &> /dev/null; then
    echo "Connected."
    
    # Update Logic
    UPDATED=false
    
    # Method 1: Git Pull
    if [ -d ".git" ] && command -v git &> /dev/null; then
        echo "Git repository detected. Updating via git..."
        git pull origin main
        if [ $? -eq 0 ]; then
            UPDATED=true
            echo "Git update successful."
        else
            echo "Git update failed. Trying direct download..."
        fi
    fi
    
    # Method 2: HTTP Download (if Method 1 didn't run or failed)
    # We check if we already updated successfully to avoid double work
    if [ "$UPDATED" = false ]; then
        echo "Downloading latest version from GitHub..."
        curl -L -o update.zip "https://github.com/chunhua523/GEX_Scraper/archive/refs/heads/main.zip"
        
        if [ -f "update.zip" ]; then
            echo "Download complete. Extracting..."
            # Unzip quietly (-q) and overwrite (-o)
            unzip -q -o update.zip
            
            # GitHub zip usually extracts to "RepoName-branchName" e.g. GEX_Scraper-main
            if [ -d "GEX_Scraper-main" ]; then
                echo "Applying updates..."
                # Copy contents to current dir, overwriting
                cp -R GEX_Scraper-main/* .
                
                # Copy hidden files if any (like .gitignore, though usually not critical for runtime)
                # cp -R GEX_Scraper-main/.* . 2>/dev/null 
                
                # Cleanup
                rm -rf GEX_Scraper-main
                rm update.zip
                echo "Update fully applied."
            else
                echo "Error: Update folder structure unexpected."
            fi
        else
            echo "Download failed."
        fi
    fi
else
    echo "No internet connection. Skipping update check."
fi

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    echo "Please install Python 3 from https://www.python.org/downloads/"
    echo "Press any key to exit..."
    read -n 1
    exit 1
fi

# Prefer non-CLT Python to avoid old Tk (8.5)
PYTHON_BIN="python3"
if [ -x "/opt/homebrew/bin/python3" ]; then
    PYTHON_BIN="/opt/homebrew/bin/python3"
elif [ -x "/usr/local/bin/python3" ]; then
    PYTHON_BIN="/usr/local/bin/python3"
fi

# Validate base Python Tk version before creating venv
if ! "$PYTHON_BIN" - <<'PY' > /dev/null 2>&1
import tkinter as tk
import sys
sys.exit(0 if tk.TkVersion >= 8.6 else 1)
PY
then
    echo "Error: Detected Tk < 8.6 from $PYTHON_BIN."
    echo "This can cause blank/empty GUI windows on macOS."
    echo "Install a newer Python (python.org installer is OK), then rerun."
    echo "Download: https://www.python.org/downloads/macos/"
    exit 1
fi

# Virtual Environment Setup
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment (.venv)..."
    "$PYTHON_BIN" -m venv .venv
fi

# Activate Virtual Environment
source .venv/bin/activate

# If existing venv is backed by an old Tk runtime, rebuild it.
if ! python - <<'PY' > /dev/null 2>&1
import tkinter as tk
import sys
sys.exit(0 if tk.TkVersion >= 8.6 else 1)
PY
then
    echo "Detected old Tk runtime inside .venv. Recreating virtual environment..."
    deactivate 2>/dev/null || true
    rm -rf .venv
    "$PYTHON_BIN" -m venv .venv
    source .venv/bin/activate
fi

# Install/Update Dependencies
echo "Checking dependencies..."
# Upgrade pip to avoid warnings
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright Browsers
# Only install if browsers validation fails? 
# Playwright install is idempotent but can be slow to check.
# We'll just run it, usually it's fast if already installed.
echo "Verifying browser binaries..."
playwright install chromium

# Run Application
echo "Starting Lieta Scraper..."
python main.py
