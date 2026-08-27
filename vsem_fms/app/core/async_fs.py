import hashlib
import os
import time
import uuid
from typing import Any

from anyio import Path as AsyncPath
from anyio import open_file, to_thread
from fastapi import UploadFile
from loguru import logger

from vsem_fms.app.config import settings
from vsem_fms.app.exceptions.file_exceptions import FileSizeError, FolderNotFoundError


class AsyncFileManager:
    """Asynchronous filesystem operations for VSEM FMS."""

    def __init__(self) -> None:
        self.base_dir = AsyncPath(settings.STORAGE_PATH)

    def _hash_value(self, value: Any) -> str:
        return hashlib.sha256(str(value).encode()).hexdigest()

    def _get_hashed_path(
        self,
        folder: str,
        subfolder: str,
        filename: str | None = None,
    ) -> AsyncPath:
        """Build the internal hashed folder/subfolder path."""
        folder_hash = self._hash_value(folder)
        subfolder_hash = self._hash_value(subfolder)
        path = self.base_dir / folder_hash / subfolder_hash
        return path / filename if filename else path

    def _get_hashed_filename(self, original_filename: str) -> str:
        """Return the legacy v1.0.0 hashed filename for backward compatibility."""
        extension = os.path.splitext(original_filename)[1]
        return f"{self._hash_value(original_filename)}{extension}"

    def _validate_filename(self, filename: str | None) -> str:
        """Reject empty or path-like filenames before using them on disk."""
        if not filename or filename in {".", ".."} or "/" in filename or "\\" in filename or "\x00" in filename:
            raise ValueError("Invalid filename")
        return filename

    def _file_candidates(self, folder: str, subfolder: str, filename: str) -> tuple[AsyncPath, AsyncPath]:
        """Return the current and legacy storage paths for a logical filename."""
        safe_filename = self._validate_filename(filename)
        current = self._get_hashed_path(folder, subfolder, safe_filename)
        legacy = self._get_hashed_path(folder, subfolder, self._get_hashed_filename(safe_filename))
        return current, legacy

    async def _ensure_dir(self, path: AsyncPath) -> None:
        """Create a directory safely when concurrent requests race to create it."""
        await path.mkdir(parents=True, exist_ok=True)

    async def _check_dir_exists(self, path: AsyncPath, folder: str, subfolder: str) -> None:
        if not await path.exists():
            logger.warning("Directory not found: folder='{}', subfolder='{}'", folder, subfolder)
            raise FolderNotFoundError(folder=folder, subfolder=subfolder)

    async def _check_file_exists(self, file_path: AsyncPath, filename: str) -> None:
        if not await file_path.exists():
            logger.warning("File not found: '{}'", filename)
            raise FileNotFoundError(f"File {filename} not found")

    async def _resolve_file_path(self, folder: str, subfolder: str, filename: str) -> AsyncPath:
        """Resolve a logical filename, including legacy v1.0.0 hashed storage."""
        current, legacy = self._file_candidates(folder, subfolder, filename)
        await self._check_dir_exists(current.parent, folder, subfolder)

        if await current.exists():
            return current
        if await legacy.exists():
            return legacy

        raise FileNotFoundError(f"File {filename} not found")

    async def _write_file_stream(self, file: UploadFile, directory: AsyncPath) -> AsyncPath:
        """Write upload data to a temporary file and enforce the size limit."""
        await self._ensure_dir(directory)

        max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        total_size = 0
        temp_path = directory / f".upload-{uuid.uuid4().hex}.tmp"

        try:
            async with await open_file(temp_path, "xb") as dest_file:
                while chunk := await file.read(1024 * 1024):
                    total_size += len(chunk)
                    if total_size > max_size:
                        raise FileSizeError(size=total_size, limit=max_size)
                    await dest_file.write(chunk)
        except BaseException:
            if await temp_path.exists():
                await temp_path.unlink()
            raise

        return temp_path

    async def _commit_temp_file(self, temp_path: AsyncPath, final_path: AsyncPath, overwrite: bool) -> None:
        """Atomically commit a complete temp file to its final location."""
        if overwrite:
            await to_thread.run_sync(os.replace, str(temp_path), str(final_path))
            return

        try:
            await to_thread.run_sync(os.link, str(temp_path), str(final_path))
        except FileExistsError:
            raise
        finally:
            if await temp_path.exists():
                await temp_path.unlink()

    async def save_file(
        self,
        file: UploadFile,
        folder: str,
        subfolder: str,
        *,
        overwrite: bool = True,
    ) -> AsyncPath:
        """Save a file using temp-write + atomic commit semantics."""
        filename = self._validate_filename(file.filename)
        final_path, legacy_path = self._file_candidates(folder, subfolder, filename)
        await self._ensure_dir(final_path.parent)

        if not overwrite and (await final_path.exists() or await legacy_path.exists()):
            raise FileExistsError(f"File {filename} already exists")

        temp_path = await self._write_file_stream(file=file, directory=final_path.parent)

        try:
            await self._commit_temp_file(temp_path=temp_path, final_path=final_path, overwrite=overwrite)
        except BaseException:
            if await temp_path.exists():
                await temp_path.unlink()
            raise

        if legacy_path != final_path and await legacy_path.exists():
            await legacy_path.unlink()

        logger.info("File saved successfully: '{}'", filename)
        return final_path

    async def get_file_path(self, folder: str, subfolder: str, filename: str) -> AsyncPath:
        """Return the internal path for a logical file after existence checks."""
        return await self._resolve_file_path(folder=folder, subfolder=subfolder, filename=filename)

    async def read_file(self, folder: str, subfolder: str, filename: str) -> bytes:
        """Read a file into memory. Used only for inline text responses."""
        file_path = await self._resolve_file_path(folder=folder, subfolder=subfolder, filename=filename)
        async with await open_file(file_path, "rb") as file_obj:
            return await file_obj.read()

    async def delete_file(self, folder: str, subfolder: str, filename: str) -> bool:
        """Delete a logical file, supporting both current and legacy storage names."""
        current, legacy = self._file_candidates(folder, subfolder, filename)
        await self._check_dir_exists(current.parent, folder, subfolder)

        deleted = False
        for file_path in {current, legacy}:
            if await file_path.exists():
                await file_path.unlink()
                deleted = True

        if not deleted:
            raise FileNotFoundError(f"File {filename} not found")

        logger.info("File deleted: '{}/{}/{}'", folder, subfolder, filename)
        return True

    async def list_files(self, folder: str, subfolder: str) -> list[str]:
        """List logical filenames without exposing absolute server paths."""
        target_dir = self._get_hashed_path(folder=folder, subfolder=subfolder)
        await self._check_dir_exists(target_dir, folder, subfolder)

        files: list[str] = []
        async for file_path in target_dir.iterdir():
            if await file_path.is_file() and not file_path.name.startswith(".upload-"):
                files.append(file_path.name)

        return sorted(files)

    async def cleanup_old_files(self) -> None:
        """Delete files older than MAX_FILE_AGE_HOURS recursively."""
        await self._ensure_dir(self.base_dir)
        now = time.time()

        async for file_path in self.base_dir.rglob("*"):
            if await file_path.is_file():
                modified_time = (await file_path.stat()).st_mtime
                age_hours = (now - modified_time) / 3600
                if age_hours > settings.MAX_FILE_AGE_HOURS:
                    await file_path.unlink()
                    logger.info("Deleted old file: {}", file_path)
