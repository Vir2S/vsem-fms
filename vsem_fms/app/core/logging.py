import sys
from pathlib import Path

from loguru import logger

from vsem_fms.app.config import settings


_logging_configured = False

_TEXT_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "request_id={extra[request_id]} | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)
_FILE_TEXT_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss} | {level} | request_id={extra[request_id]} | "
    "{name}:{function}:{line} - {message}"
)


def setup_logging() -> None:
    """Configure application logging from settings."""
    global _logging_configured

    if _logging_configured:
        return

    log_level = settings.LOG_LEVEL.upper()
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    serialize = settings.LOG_FORMAT == "json"

    logger.remove()
    logger.configure(extra={"request_id": "-"})
    logger.add(
        sys.stdout,
        level=log_level,
        format=_TEXT_FORMAT,
        serialize=serialize,
        diagnose=False,
        catch=True,
    )
    logger.add(
        log_dir / "app.log",
        level=log_level,
        format=_FILE_TEXT_FORMAT,
        serialize=serialize,
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
