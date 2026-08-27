import sys
from pathlib import Path

from loguru import logger

from vsem_fms.app.config import settings


logger.remove()

log_level = settings.LOG_LEVEL.upper()
log_dir = Path(settings.LOG_DIR)
log_dir.mkdir(parents=True, exist_ok=True)

logger.add(
    sys.stdout,
    level=log_level,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
    diagnose=False,
    backtrace=False,
    catch=True,
)

logger.add(
    str(log_dir / "app.log"),
    level=log_level,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
    encoding="utf-8",
    rotation="10 MB",
    compression="zip",
    enqueue=True,
    diagnose=False,
    backtrace=False,
)


def setup_logging() -> None:
    """Confirm that logging has been configured."""
    logger.info("Logging system initialized")


__all__ = ["logger"]
