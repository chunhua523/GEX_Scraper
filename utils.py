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
    For backward compatibility, flattens groups into a single list.
    """
    groups = load_tickers_with_groups(filepath)
    # Flatten all groups into a single list
    tickers = []
    for group_name, ticker_list in groups.items():
        tickers.extend(ticker_list)
    return tickers

def load_tickers_with_groups(filepath):
    """
    Reads tickers with groups from a JSON file.
    Returns a dict where keys are group names and values are lists of tickers.
    
    Format: {"Group1": ["TICK1", "TICK2"], "Group2": ["TICK3"]}
    
    If the file is in old plain text format, it will be automatically migrated.
    """
    import json
    
    if not os.path.exists(filepath):
        return {"Default": []}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
        # Try to parse as JSON first
        try:
            data = json.loads(content)
            # Validate structure
            if isinstance(data, dict):
                return data
            else:
                # Invalid JSON structure, treat as legacy
                raise ValueError("Invalid JSON structure")
        except (json.JSONDecodeError, ValueError):
            # Legacy plain text format - migrate it
            parts = re.split(r'[,\n]+', content)
            tickers = [p.strip() for p in parts if p.strip()]
            migrated_data = {"Default": tickers}
            
            # Auto-save migrated format
            save_tickers_with_groups(filepath, migrated_data)
            
            return migrated_data
    except Exception as e:
        print(f"Error loading ticker file {filepath}: {e}")
        return {"Default": []}

def save_tickers_with_groups(filepath, groups_dict):
    """
    Saves tickers with groups to a JSON file.
    
    Args:
        filepath: Path to save the file
        groups_dict: Dict with group names as keys and ticker lists as values
                     Example: {"Tech": ["AAPL", "MSFT"], "Finance": ["JPM"]}
    """
    import json
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(groups_dict, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving ticker file {filepath}: {e}")
        return False

def get_ticker_group(filepath, ticker):
    """
    Returns the group name that contains the given ticker.
    Returns None if ticker is not found.
    """
    groups = load_tickers_with_groups(filepath)
    for group_name, ticker_list in groups.items():
        if ticker in ticker_list:
            return group_name
    return None
