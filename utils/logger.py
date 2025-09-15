#!/usr/bin/env python3
"""
EZREC Standardized Logging Utilities
Provides consistent logging configuration across all services
"""

import logging
import sys
from typing import Optional
from pathlib import Path

class EZRECFormatter(logging.Formatter):
    """Custom formatter for EZREC logs"""
    
    # Color codes for different log levels
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # Add color to level name
        if hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{color}{record.levelname}{self.RESET}"
        
        return super().format(record)

def get_logger(name: str, 
               level: str = "INFO",
               log_file: Optional[Path] = None,
               use_colors: bool = True) -> logging.Logger:
    """
    Get a configured logger for EZREC services
    
    Args:
        name: Logger name (usually __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file to write logs to
        use_colors: Whether to use colored output
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding multiple handlers
    if logger.handlers:
        return logger
    
    # Set log level
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Create formatter
    if use_colors and sys.stdout.isatty():
        formatter = EZRECFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def setup_service_logging(service_name: str, 
                         log_dir: Path = Path("/opt/ezrec-backend/logs"),
                         level: str = "INFO") -> logging.Logger:
    """
    Setup logging for a service with file output
    
    Args:
        service_name: Name of the service
        log_dir: Directory to store log files
        level: Log level
    
    Returns:
        Configured logger
    """
    log_file = log_dir / f"{service_name}.log"
    return get_logger(service_name, level, log_file)

class LogContext:
    """Context manager for adding context to logs"""
    
    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
        self.old_factory = None
    
    def __enter__(self):
        # Store old record factory
        self.old_factory = logging.getLogRecordFactory()
        
        # Create new factory with context
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore old factory
        logging.setLogRecordFactory(self.old_factory)

def log_function_call(func):
    """Decorator to log function calls"""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} failed: {e}")
            raise
    return wrapper

def log_execution_time(func):
    """Decorator to log function execution time"""
    import time
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func.__name__} executed in {execution_time:.2f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.2f}s: {e}")
            raise
    
    return wrapper
