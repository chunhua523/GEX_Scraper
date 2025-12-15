# Lieta Scraper

## Windows Installation & Run
1. Install Python 3.
2. Double click `run.bat` (if exists) or run `python main.py` in terminal.

## macOS Installation & Run

To ensure the application runs smoothly on macOS and updates automatically:

### 1. Prerequisites
- **Python 3**: Ensure you have Python 3 installed. You can check by opening Terminal and typing `python3 --version`. If not installed, download from [python.org](https://www.python.org/downloads/).
- **Git**: Ensure Git is installed (usually pre-installed or installed via Xcode Command Line Tools).

### 2. First Time Setup
1. Open **Terminal**.
2. Navigate to the project folder. e.g.:
   ```bash
   cd /path/to/GEX_scraper
   ```
3. Make the runner script executable (only needed once):
   ```bash
   chmod +x run_on_mac.sh
   ```

### 3. How to Run
Every time you want to use the scraper:
1. Open **Terminal**.
2. Drag and drop the `run_on_mac.sh` file into the terminal window (or type `./run_on_mac.sh`).
3. Press **Enter**.

The script will automatically:
1. Check for code updates from GitHub.
2. Install any missing libraries.
3. Launch the application.

> **Note**: The first run might take a few minutes to download the necessary browser binaries (Chromium).

### Troubleshooting
- If you see "Permission denied", make sure you ran `chmod +x run_on_mac.sh`.
- If the window doesn't appear, check the terminal for error messages.
