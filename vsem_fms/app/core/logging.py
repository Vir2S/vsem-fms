import sys

from loguru import logger


# Remove default logging handlers to prevent duplicate logs
logger.remove()

# Add logistics in Stdout with an Info level for all messages
logger.add(
    sys.stdout,
    level="INFO",
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
    diagnose=True,
    catch=True,
)

# Error logging in a rotation file (old log files will be deleted when 10 mb reaches)
logger.add(
    "logs/app.log",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
    encoding="utf-8",
    rotation="10 MB",
    compression="zip",
    enqueue=True,
)


def setup_logging():
    """
    Initializes the logging system.

    This function ensures that logging is properly set up
    before the application starts.
    """
    logger.info("Logging system initialized")


__all__ = ["logger"]
