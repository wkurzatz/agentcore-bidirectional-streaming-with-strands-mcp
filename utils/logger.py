"""Logging configuration for AgentCore Runtime."""

import logging
import os
import sys


def get_log_level() -> int:
    """Get log level from environment variable."""
    log_level_name = os.environ.get('LOG_LEVEL', 'INFO')
    return getattr(logging, log_level_name.upper(), logging.INFO)


def setup_logger(name: str = __name__, level: int = None) -> logging.Logger:
    """
    Set up and configure logger.
    
    Args:
        name: Logger name
        level: Logging level (defaults to LOG_LEVEL env var, or INFO)
        
    Returns:
        Configured logger instance
    """
    if level is None:
        level = get_log_level()
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    if not logger.handlers:
        logger.addHandler(handler)
    
    return logger

# Create default logger
logger = setup_logger('agentcore')
