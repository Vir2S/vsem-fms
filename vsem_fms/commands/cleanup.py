import asyncio

from loguru import logger

from vsem_fms.app.config import settings
from vsem_fms.app.core.async_fs import AsyncFileManager
from vsem_fms.app.core.logging import setup_logging


async def run_cleanup_loop() -> None:
    """Run retention cleanup forever using the configured interval."""
    manager = AsyncFileManager()
    while True:
        try:
            deleted = await manager.cleanup_old_files()
            logger.info("Cleanup cycle completed: {} file(s) deleted", deleted)
        except Exception:
            logger.exception("Cleanup cycle failed")
        await asyncio.sleep(settings.CLEANUP_INTERVAL_SECONDS)


def main() -> None:
    setup_logging()
    asyncio.run(run_cleanup_loop())


if __name__ == "__main__":
    main()
