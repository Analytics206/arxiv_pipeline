import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logger(name, log_level=None):
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Configure logger
    logger = logging.getLogger(name)
    
    # Check if handlers already exist to avoid duplicates
    if not logger.handlers:
        # Default log level if not specified
        if log_level is None:
            log_level = logging.INFO
        
        logger.setLevel(log_level)
        
        # Create a file handler for writing to log file
        log_file = os.path.join(logs_dir, f"{name}.log")
        file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
        file_handler.setLevel(log_level)
        
        # Create a console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        
        # Create formatter and add to handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger