"""Structured application logging for RFP Intelligence Platform."""

import logging
import sys
from typing import Optional
from app.config import get_settings


def setup_logger(name: Optional[str] = None) -> logging.Logger:
    """Set up and configure a structured logger."""
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logger = logging.getLogger(name or "rfp_intelligence")
    
    if not logger.handlers:
        logger.setLevel(log_level)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False

    return logger


logger = setup_logger("rfp_intelligence")
