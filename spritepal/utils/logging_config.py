"""Logging configuration for SpritePal"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional


def setup_logging(log_dir: Optional[Path] = None, log_level: str = "INFO") -> logging.Logger:
    """
    Configure application-wide logging.

    Args:
        log_dir: Directory for log files (defaults to ~/.spritepal/logs)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    if log_dir is None:
        log_dir = Path.home() / ".spritepal" / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)

    # Configure root logger for spritepal
    logger = logging.getLogger("spritepal")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler with simplified format
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "%(levelname)s - %(name)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)

    # File handler with detailed format and rotation
    log_file = log_dir / "spritepal.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5_000_000,  # 5MB
        backupCount=3
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Log startup
    logger.info(f"SpritePal logging initialized. Log file: {log_file}")

    return logger


def get_logger(module_name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    Args:
        module_name: Name of the module requesting the logger

    Returns:
        Logger instance for the module
    """
    return logging.getLogger(f"spritepal.{module_name}")
