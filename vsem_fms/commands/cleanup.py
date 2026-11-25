import asyncio
import signal

from loguru import logger

from vsem_fms.app.config import settings
from vsem_fms.app.storage.dependencies import storage_backend_context
from vsem_fms.app.core.logging import setup_logging


async def run_cleanup_loop() -> None:
    """Run retention cleanup forever using the configured interval."""
    async with storage_backend_context() as manager:
        while True:
            try:
                deleted = await manager.cleanup_old_files()
                logger.info("Cleanup cycle completed: {} file(s) deleted", deleted)
            except Exception:
                logger.exception("Cleanup cycle failed")
            await asyncio.sleep(settings.CLEANUP_INTERVAL_SECONDS)


async def _run_cleanup_worker() -> None:
    """Translate SIGTERM into cancellation so Docker can shut down the pool."""
    loop = asyncio.get_running_loop()
    task = asyncio.current_task()
    registered = False
    if task is not None:
        try:
            loop.add_signal_handler(signal.SIGTERM, task.cancel)
            registered = True
        except (NotImplementedError, RuntimeError):
            # Some platforms do not support asyncio signal handlers.
            pass
    try:
        await run_cleanup_loop()
    finally:
        if registered:
            loop.remove_signal_handler(signal.SIGTERM)


def main() -> None:
    setup_logging()
    try:
        asyncio.run(_run_cleanup_worker())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass


if __name__ == "__main__":
    main()
