"""Compatibility logging for FastMCP."""

import logging


def get_logger(name: str) -> logging.Logger:
    """Get logger instance."""
    return logging.getLogger(name)


__all__ = ["get_logger"]
