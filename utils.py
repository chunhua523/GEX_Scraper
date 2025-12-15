import logging
import os
import re
from datetime import datetime

def setup_logging(log_widget=None):
    """
    Sets up logging configuration.
    If log_widget is provided, it should have a .write() method (like a Text widget wrapper).
    """
    logger = logging.getLogger("LietaScraper")
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')

    # Console Handler
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger

def get_timestamp_filename(prefix="data", extension=".txt"):
    """
    Returns a filename with current timestamp.
    e.g. data_20241025_120000.txt
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}{extension}"

def clean_filename(filename):
    """
    Sanitizes a string to be safe for filenames.
    """
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def load_tickers_from_file(filepath):
    """
    Reads tickers from a file (txt or csv). 
    Assumes one ticker per line or comma separated.
    """
    tickers = []
    if not os.path.exists(filepath):
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        # Split by newline or comma
        parts = re.split(r'[,\n]+', content)
        tickers = [p.strip() for p in parts if p.strip()]
    
    return tickers
