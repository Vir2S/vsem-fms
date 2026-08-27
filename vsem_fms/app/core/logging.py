import sys
from pathlib import Path

from loguru import logger

from vsem_fms.app.config import settings


_logging_configured = False


def setup_logging() -> None:
    """Configure application logging from settings."""
    global _logging_configured

    if _logging_configured:
        return

    log_level = settings.LOG_LEVEL.upper()
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.remove()
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
        catch=True,
    )
    logger.add(
        log_dir / "app.log",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
        encoding="utf-8",
        rotation="10 MB",
        compression="zip",
        enqueue=True,
        diagnose=False,
        catch=True,
    )

    _logging_configured = True
    logger.info("Logging system initialized")


__all__ = ["logger", "setup_logging"]
