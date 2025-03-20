import sys

from loguru import logger

# Remove default logging handlers to prevent duplicate logs
logger.remove()

# Configure Loguru to log messages to stdout with a specific format
logger.add(
    sys.stdout,
    format="{time} {level} {message}",
    level="INFO"
)


def setup_logging():
    """
    Initializes the logging system.

    This function ensures that logging is properly set up
    before the application starts.
    """
    logger.info("Logging system initialized")


__all__ = ["logger"]
