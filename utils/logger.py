"""
Logging configuration for CyberScore
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from config import settings


def setup_logging():
    """Setup logging configuration"""

    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / settings.log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Create logger
    logger = logging.getLogger("cyberscore")

    return logger


def get_logger(name: str = "cyberscore"):
    """Get a logger instance"""
    return logging.getLogger(name)


# Global logger instance
logger = setup_logging()
