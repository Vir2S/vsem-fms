import hashlib
import os
import time
from typing import Any
from uuid import uuid4

from anyio import Path as AsyncPath
from anyio import open_file
from fastapi import UploadFile
from loguru import logger

from vsem_fms.app.config import settings
from vsem_fms.app.exceptions.file_exceptions import (
    FileSizeError,
    FolderNotFoundError,
    InvalidFileNameError,
)


class AsyncFileManager:
    """Asynchronous file manager backed by AnyIO filesystem primitives."""

    def __init__(self) -> None:
        self.base_dir = AsyncPath(settings.STORAGE_PATH)

    def _hash_value(self, value: Any) -> str:
        """Return a deterministic SHA-256 identifier for a value."""
        return hashlib.sha256(str(value).encode()).hexdigest()

    def _get_hashed_path(
        self,
        folder: str,
        subfolder: str,
        filename: str | None = None,
    ) -> AsyncPath:
        """Build the physical path for a logical folder/subfolder pair."""
        folder_hash = self._hash_value(folder)
        subfolder_hash = self._hash_value(subfolder)
        directory = self.base_dir / folder_hash / subfolder_hash
        return directory / filename if filename else directory

    def _validate_filename(self, filename: str | None) -> str:
        """Reject empty names and path traversal while preserving the API filename."""
        if (
            not filename
            or filename in {".", ".."}
            or "/" in filename
            or "\\" in filename
            or "\x00" in filename
        ):
            raise InvalidFileNameError()
        return filename

    def _get_legacy_hashed_filename(self, original_filename: str) -> str:
        """Return the filename format used by v1.0.0 for backwards compatibility."""
        extension = os.path.splitext(original_filename)[1]
        return f"{self._hash_value(original_filename)}{extension}"

    async def _ensure_dir(self, path: AsyncPath) -> None:
        if not await path.exists():
            await path.mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 Created directory: {path}")

    async def _check_dir_exists(self, path: AsyncPath, folder: str, subfolder: str) -> None:
        if not await path.exists():
            logger.warning(f"📂 Directory not found: folder='{folder}', subfolder='{subfolder}'")
            raise FolderNotFoundError(folder=folder, subfolder=subfolder)

    async def _resolve_existing_file_path(
        self,
        folder: str,
        subfolder: str,
        filename: str,
    ) -> AsyncPath:
        """Resolve current filenames first and v1.0.0 hashed filenames second."""
        safe_filename = self._validate_filename(filename)
        directory = self._get_hashed_path(folder=folder, subfolder=subfolder)
        await self._check_dir_exists(path=directory, folder=folder, subfolder=subfolder)

        current_path = directory / safe_filename
        if await current_path.is_file():
            return current_path

        legacy_path = directory / self._get_legacy_hashed_filename(safe_filename)
        if await legacy_path.is_file():
            return legacy_path

        logger.warning(f"❌ File not found: '{safe_filename}' at {directory}")
        raise FileNotFoundError(f"File {safe_filename} not found in {directory}")

    async def _write_file_stream(self, file: UploadFile, save_path: AsyncPath) -> int:
        """Write an upload to a temporary file and atomically replace the target."""
        await self._ensure_dir(save_path.parent)

        max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        total_size = 0
        temp_path = save_path.parent / f".{save_path.name}.{uuid4().hex}.tmp"

        try:
            async with await open_file(temp_path, "wb") as dest_file:
                while chunk := await file.read(1024 * 1024):
                    total_size += len(chunk)
                    if total_size > max_size:
                        logger.error(
                            f"❌ File too large: {total_size} bytes > {max_size} bytes — {save_path.name}"
                        )
                        raise FileSizeError(size=total_size, limit=max_size)
                    await dest_file.write(chunk)

            await temp_path.replace(save_path)
        except Exception:
            if await temp_path.exists():
                await temp_path.unlink()
            raise

        logger.info(f"✅ File saved successfully: {save_path.name}, size={total_size} bytes")
        return total_size

    async def save_file(
        self,
        file: UploadFile,
        folder: str,
        subfolder: str,
        *,
        overwrite: bool = True,
    ) -> AsyncPath:
        """Save an uploaded file while preserving its public filename."""
        filename = self._validate_filename(file.filename)
        directory = self._get_hashed_path(folder=folder, subfolder=subfolder)
        full_path = directory / filename
        legacy_path = directory / self._get_legacy_hashed_filename(filename)

        await self._ensure_dir(path=directory)

        current_exists = await full_path.exists()
        legacy_exists = await legacy_path.exists()
        if not overwrite and (current_exists or legacy_exists):
            logger.warning(f"⚠️ File already exists and overwrite is False: {filename}")
            raise FileExistsError(f"File {filename} already exists.")

        try:
            await self._write_file_stream(file=file, save_path=full_path)
        except OSError:
            logger.exception(
                f"❌ Failed to save file {filename} in folder={folder}, subfolder={subfolder}"
            )
            raise

        if legacy_exists and legacy_path != full_path and await legacy_path.exists():
            try:
                await legacy_path.unlink()
                logger.info(f"Migrated legacy stored filename for '{filename}'")
            except OSError:
                logger.warning(f"Could not remove legacy duplicate for '{filename}'")

        return full_path

    async def read_file(self, folder: str, subfolder: str, filename: str) -> bytes:
        """Read a file by its public filename, including legacy v1.0.0 storage."""
        file_path = await self._resolve_existing_file_path(
            folder=folder,
            subfolder=subfolder,
            filename=filename,
        )

        async with await open_file(file_path, "rb") as file_handle:
            content = await file_handle.read()

        logger.info(f"File {filename} read successfully")
        return content

    async def delete_file(self, folder: str, subfolder: str, filename: str) -> None:
        """Delete a file by the same public filename used by GET and POST."""
        file_path = await self._resolve_existing_file_path(
            folder=folder,
            subfolder=subfolder,
            filename=filename,
        )
        await file_path.unlink()
        logger.info(f"🗑️ File deleted: {file_path}")

    async def list_files(self, folder: str, subfolder: str) -> list[str]:
        """List filenames only, without leaking physical storage paths."""
        target_dir = self._get_hashed_path(folder=folder, subfolder=subfolder)
        await self._check_dir_exists(path=target_dir, folder=folder, subfolder=subfolder)

        files = [
            entry.name
            async for entry in target_dir.iterdir()
            if await entry.is_file() and not entry.name.endswith(".tmp")
        ]
        return sorted(files)

    async def cleanup_old_files(self) -> None:
        """Delete files older than ``MAX_FILE_AGE_HOURS`` recursively."""
        await self._ensure_dir(path=self.base_dir)
        now = time.time()

        async for file_path in self.base_dir.rglob("*"):
            if await file_path.is_file():
                modified_time = (await file_path.stat()).st_mtime
                age_hours = (now - modified_time) / 3600
                if age_hours > settings.MAX_FILE_AGE_HOURS:
                    await file_path.unlink()
                    logger.info(f"🗑️ Deleted old file: {file_path}")

        logger.info("✅ Cleanup of old files completed.")
