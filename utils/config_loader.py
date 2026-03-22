import yaml
import logging
import os
from datetime import datetime, timezone, timedelta

# Define IST timezone (UTC + 5 hours 30 minutes)
IST = timezone(timedelta(hours=5, minutes=30))

def load_config():
    # Dynamically resolve path two directories up to find config.yaml
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config.yaml")
    
    with open(config_path, 'r') as stream:
        return yaml.safe_load(stream)

def setup_logging(module_name):
    """Sets up standard, clean console logging forced to IST."""
    logger = logging.getLogger(module_name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Console Handler (Standard text output only, no file creation)
        ch = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        
        # Override the default converter to force IST on the console
        formatter.converter = lambda *args: datetime.now(IST).timetuple()
        ch.setFormatter(formatter)
        
        logger.addHandler(ch)
        
    return logger