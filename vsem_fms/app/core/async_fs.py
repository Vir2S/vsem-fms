import hashlib
import os
import time
from typing import Any

from anyio import (
    Path as AsyncPath,
    open_file,
)
from fastapi import UploadFile
from loguru import logger

from vsem_fms.app.config import settings
from vsem_fms.app.exceptions.file_exceptions import FolderNotFoundError


class AsyncFileManager:
    """
    Asynchronous File Manager for non-blocking filesystem operations using anyio.
    Handles file I/O operations like reading, writing, deleting, and listing files.
    """

    def __init__(self):
        """
        Initialize with base storage directory.
        """
        self.base_dir = AsyncPath(settings.STORAGE_PATH)

    def _hash_value(self, value: Any) -> str:
        """
        Generate a unique string identifier for a given value.

        Args:
            value (int): The integer value to be hashed.

        Returns:
            str: The resulting hash in hexadecimal format.
        """
        return hashlib.sha256(str(value).encode()).hexdigest()

    def _get_hashed_path(self, folder: str, subfolder: str, filename: str | None = None) -> AsyncPath:
        """
        Build a hashed full_path_to_file for the given folder, subfolder, and optional filename.

        TODO: Make the method more abstract to handle deeper nesting.

        Args:
            folder (str): The name of the parent directory.
            subfolder (str): The name of the subdirectory.
            filename (str | None): Filename. Defaults to None.

        Returns:
            AsyncPath: Full full_path_to_file to the file or directory.
        """
        folder_hash = self._hash_value(value=folder)
        subfolder_hash = self._hash_value(value=subfolder)
        full_path_to_file = self.base_dir / folder_hash / subfolder_hash
        return full_path_to_file / filename if filename else full_path_to_file

    async def _ensure_dir(self, path: AsyncPath) -> None:
        """
        Ensure the target directory exists, creating it if necessary.

        Args:
            path (AsyncPath): Directory to validate or create.
        """
        if not await path.exists():
            await path.mkdir(parents=True)
            logger.info(f"📁 Created directory: {path}")

    async def _check_dir_exists(self, path: AsyncPath, folder: str, subfolder: str) -> None:
        """
        Check if the directory exists, raising an error if it doesn't.

        Args:
            path (AsyncPath): Directory to check.
            folder (str): The name of the parent directory.
            subfolder (str): The name of the subdirectory.

        Raises:
            FolderNotFoundError: If the directory does not exist.
        """
        if not await path.exists():
            logger.warning(f"📂 Directory not found: folder='{folder}', subfolder='{subfolder}'")
            raise FolderNotFoundError(folder=folder, subfolder=subfolder)

    async def _check_file_exists(self, file_path: AsyncPath, filename: str) -> None:
        """
        Check if the file exists.

        Args:
            file_path (AsyncPath): Path to the file.
            filename (str): Name of the file.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        if not await file_path.exists():
            logger.warning(f"❌ File not found: '{filename}' at {file_path.parent}")
            raise FileNotFoundError(f"❌ File {filename} not found in {file_path.parent}")

    async def _write_file_stream(self, file: UploadFile, save_path: AsyncPath) -> str:
        """
        Asynchronously writes a file in chunks and validates the file size during writing.

        Args:
            file (UploadFile): The uploaded file object.
            save_path (AsyncPath): Full path to save the file.

        Returns:
            str: The full path to the saved file.

        Raises:
            ValueError: If the file exceeds the maximum allowed size.
        """
        await self._ensure_dir(save_path.parent)

        max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        total_size = 0

        async with await open_file(save_path, "wb") as dest_file:
            while chunk := await file.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > max_size:
                    logger.error(
                        f"❌ File too large: {total_size} bytes > {max_size} bytes — {save_path.name}. Deleting..."
                    )
                    if await save_path.exists():
                        await save_path.unlink()
                    raise ValueError(
                        f"❌ File {save_path.name} exceeds the max allowed size of {settings.MAX_FILE_SIZE_MB}MB."
                    )
                await dest_file.write(chunk)

        logger.info(f"✅ File saved successfully: {save_path.name}, size={total_size} bytes")
        return str(save_path)

    def _get_hashed_filename(self, original_filename: str) -> str:
        """
        Generate a hashed filename based on the original filename.

        Args:
            original_filename (str): The original filename to hash.

        Returns:
            str: The hashed filename with the original file extension.
        """
        extension = os.path.splitext(original_filename)[1]
        hashed_name = self._hash_value(original_filename)

        return f"{hashed_name}{extension}"

    async def save_file(
        self,
        file: UploadFile,
        folder: str,
        subfolder: str,
        *,
        overwrite: bool = True,
    ) -> AsyncPath:
        """
        Save an uploaded file to disk with validation and streaming.

        Args:
            file (UploadFile): Uploaded file.
            folder (str): The name of the parent directory.
            subfolder (str): The name of the subdirectory.
            overwrite (bool): Whether to overwrite if the file exists. Defaults to True.

        Returns:
            AsyncPath: Saved file path.

        Raises:
            FileExistsError: If the file exists and overwrite is False.
            ValueError: If the file size exceeds the limit.
            IOError: If writing to disk fails.
        """
        file_name = self._get_hashed_filename(original_filename=file.filename)

        # Obtain a hashed path to save the file
        full_path = self._get_hashed_path(folder=folder, subfolder=subfolder, filename=file_name)

        # Ensure that the parent directory exists, creating it if necessary
        await self._ensure_dir(path=full_path.parent)

        # Check for file existence and decide whether to overwrite
        if not overwrite and await full_path.exists():
            logger.warning(f"⚠️ File already exists and overwrite is False: {full_path}")
            raise FileExistsError(f"File {full_path} already exists.")

        # Write the file to disk using asynchronous I/O
        try:
            await self._write_file_stream(file=file, save_path=full_path)
            return full_path

        except IOError as e:
            logger.error(f"❌ Failed to save file {file_name} in folder={folder}, subfolder={subfolder}: {str(e)}")
            raise

    async def read_file(self, folder: str, subfolder: str, filename: str) -> bytes:
        """
        Read a file asynchronously from the specified folder and subfolder.

        Args:
            folder (str): User ID.
            subfolder (str): Project ID.
            filename (str): File name.

        Returns:
            bytes: File content.

        Raises:
            FileNotFoundError: If the file or directory does not exist.
        """
        hashed_filename = self._get_hashed_filename(original_filename=filename)

        file_path = self._get_hashed_path(folder=folder, subfolder=subfolder, filename=hashed_filename)
        logger.info(f"Trying to read file from path: {file_path}")

        await self._check_dir_exists(path=file_path.parent, folder=folder, subfolder=subfolder)
        await self._check_file_exists(file_path=file_path, filename=hashed_filename)

        async with await open_file(file_path, "rb") as f:
            content = await f.read()
            logger.info(f"File {filename} read successfully")
            return content

    async def delete_file(self, folder: str, subfolder: str, filename: str) -> bool:
        """
        Delete a file asynchronously if it exists.

        Args:
            folder (str): for example, User ID.
            subfolder (str): for example, Project ID.
            filename (str): File name.

        Returns:
            bool: True if deleted, False if not found.

        Raises:
            FileNotFoundError: If the file or directory does not exist.
        """
        file_path = self._get_hashed_path(folder=folder, subfolder=subfolder, filename=filename)

        await self._check_dir_exists(path=file_path.parent, folder=folder, subfolder=subfolder)
        await self._check_file_exists(file_path=file_path, filename=filename)

        await file_path.unlink()

        logger.info(f"🗑️ File deleted: {file_path}")
        return True

    async def list_files(self, folder: str, subfolder: str) -> list[str]:
        """
        List all files in the specified subfolder.

        Args:
            folder (str): User ID.
            subfolder (str): Project ID.

        Returns:
            List[str]: List of file paths.

        Raises:
            FolderNotFoundError: If the subfolder does not exist.
        """
        target_dir = self._get_hashed_path(folder=folder, subfolder=subfolder)
        await self._check_dir_exists(path=target_dir, folder=folder, subfolder=subfolder)
        files = [str(f) async for f in target_dir.rglob("*") if await f.is_file()]

        return files

    async def cleanup_old_files(self) -> None:
        """
        Delete files older than MAX_FILE_AGE_HOURS recursively.

        This method scans the storage directory and removes files whose age exceeds
        the configured maximum file age.
        """
        await self._ensure_dir(path=self.base_dir)
        now = time.time()

        async for file in self.base_dir.rglob("*"):
            if await file.is_file():
                modified_time = (await file.stat()).st_mtime
                age_hours = (now - modified_time) / 3600
                if age_hours > settings.MAX_FILE_AGE_HOURS:
                    await file.unlink()
                    logger.info(f"🗑️ Deleted old file: {file}")
        logger.info("✅ Cleanup of old files completed.")
