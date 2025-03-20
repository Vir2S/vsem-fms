import anyio
import time
from fastapi import UploadFile
from loguru import logger

from config import settings


class AsyncFileManager:
    """
    Asynchronous File Manager using anyio for non-blocking filesystem operations.
    Provides methods for handling file I/O operations such as reading, writing,
    deleting, and listing files in a specified directory.
    """

    def __init__(self):
        """Initialize the file manager with a base storage directory."""
        self.base_dir = anyio.Path(settings.STORAGE_PATH)

    async def ensure_storage_dir(self):
        """Ensures the storage directory exists. Creates it if it does not exist."""
        if not await self.base_dir.exists():
            await self.base_dir.mkdir(parents=True)
            logger.info(f"📁 Created storage directory: {self.base_dir}")

    async def write_file_stream(self, filename: str, file: UploadFile) -> str:
        """
        Writes a file asynchronously with streaming (chunked writing).

        :param filename: Name of the file.
        :param file: UploadFile object.
        :return: Path of the saved file.
        :raises ValueError: If the file exceeds the max allowed size.
        """
        await self.ensure_storage_dir()
        file_path = self.base_dir / filename

        max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024  # Convert MB to bytes
        total_size = 0  # Track file size while reading

        async with await anyio.open_file(file_path, "wb") as dest_file:
            while chunk := await file.read(1024 * 1024):  # Read in 1MB chunks
                total_size += len(chunk)
                if total_size > max_size:
                    logger.warning(f"❌ File {filename} exceeds the max allowed size. Deleting...")
                    await file_path.unlink()  # Delete the partially written file
                    raise ValueError(
                        f"❌ File {filename} exceeds the max allowed size of {settings.MAX_FILE_SIZE_MB}MB.")

                await dest_file.write(chunk)

        logger.info(f"✅ File saved: {file_path}")
        return str(file_path)

    async def read_file(self, filename: str) -> bytes:
        """
        Reads a file asynchronously.

        :param filename: Name of the file to read.
        :return: File content as bytes.
        :raises FileNotFoundError: If the file does not exist.
        """
        file_path = self.base_dir / filename
        if not await file_path.exists():
            raise FileNotFoundError(f"❌ File {filename} not found")

        async with await anyio.open_file(file_path, "rb") as f:
            return await f.read()

    async def delete_file(self, filename: str) -> bool:
        """
        Deletes a file asynchronously.

        :param filename: Name of the file to delete.
        :return: True if the file was deleted, False if the file was not found.
        """
        file_path = self.base_dir / filename
        if await file_path.exists():
            await file_path.unlink()
            logger.info(f"🗑️ File deleted: {filename}")
            return True
        return False

    async def list_files(self) -> list[str]:
        """
        Retrieves a list of files in the storage directory asynchronously.

        :return: List of file paths as strings.
        """
        await self.ensure_storage_dir()
        return [str(f) async for f in self.base_dir.iterdir() if await f.is_file()]

    async def cleanup_old_files(self):
        """
        Deletes files older than MAX_FILE_AGE_HOURS.
        """
        await self.ensure_storage_dir()
        now = time.time()

        async for file in self.base_dir.iterdir():
            if await file.is_file():
                modified_time = (await file.stat()).st_mtime
                age_hours = (now - modified_time) / 3600
                if age_hours > settings.MAX_FILE_AGE_HOURS:
                    await file.unlink()
                    logger.info(f"🗑️ Deleted old file: {file}")
