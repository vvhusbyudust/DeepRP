"""
Structured logging configuration for DeepRP.

Provides consistent logging across all modules with:
- Console output (INFO level)
- File logging (DEBUG level)
- Structured format for easy parsing
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

from config import settings


def setup_logging(
    name: str = "deeprp",
    log_file: str = "deeprp.log",
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up structured logging with console and file handlers.
    
    Args:
        name: Logger name
        log_file: Path to log file (relative to data_dir)
        console_level: Minimum level for console output
        file_level: Minimum level for file output
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    
    # Console handler - human readable format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler - detailed format with rotation
    log_path = settings.data_dir / log_file
    try:
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(file_level)
        file_format = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    except Exception as e:
        # Log to console if file logging fails, but don't crash
        console_handler.setLevel(logging.DEBUG)
        logger.warning(f"Could not set up file logging: {e}")
    
    return logger


# Create main logger instance
logger = setup_logging()


def get_logger(name: str) -> logging.Logger:
    """
    Get a child logger with the given name.
    
    Usage:
        from utils.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Something happened")
    """
    return logging.getLogger(f"deeprp.{name}")


# Convenience functions matching print-style usage
def log_debug(message: str, *args, **kwargs):
    """Log debug message (only to file by default)."""
    logger.debug(message, *args, **kwargs)


def log_info(message: str, *args, **kwargs):
    """Log info message."""
    logger.info(message, *args, **kwargs)


def log_warning(message: str, *args, **kwargs):
    """Log warning message."""
    logger.warning(message, *args, **kwargs)


def log_error(message: str, *args, **kwargs):
    """Log error message."""
    logger.error(message, *args, **kwargs)


def log_critical(message: str, *args, **kwargs):
    """Log critical message."""
    logger.critical(message, *args, **kwargs)


def log_exception(message: str, *args, **kwargs):
    """Log error message with exception traceback."""
    logger.exception(message, *args, **kwargs)
