import io
import tempfile
import unittest
from pathlib import Path

from anyio import Path as AsyncPath
from fastapi import UploadFile

from vsem_fms.app.config import settings
from vsem_fms.app.core.async_fs import AsyncFileManager
from vsem_fms.app.exceptions.file_exceptions import FileSizeError, InvalidFileNameError


class AsyncFileManagerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.manager = AsyncFileManager()
        self.manager.base_dir = AsyncPath(self.temp_dir.name)
        self.original_limit = settings.MAX_FILE_SIZE_MB

    async def asyncTearDown(self) -> None:
        settings.MAX_FILE_SIZE_MB = self.original_limit
        self.temp_dir.cleanup()

    @staticmethod
    def upload(filename: str, content: bytes) -> UploadFile:
        return UploadFile(filename=filename, file=io.BytesIO(content))

    async def test_save_list_read_and_delete_use_same_public_filename(self) -> None:
        await self.manager.save_file(
            file=self.upload("report.txt", b"hello"),
            folder="customer-1",
            subfolder="project-1",
        )

        self.assertEqual(
            await self.manager.list_files("customer-1", "project-1"),
            ["report.txt"],
        )
        self.assertEqual(
            await self.manager.read_file("customer-1", "project-1", "report.txt"),
            b"hello",
        )

        await self.manager.delete_file("customer-1", "project-1", "report.txt")
        self.assertEqual(await self.manager.list_files("customer-1", "project-1"), [])

    async def test_legacy_hashed_file_is_still_readable_and_deletable(self) -> None:
        folder = "customer-1"
        subfolder = "legacy"
        filename = "old.txt"
        directory = self.manager._get_hashed_path(folder, subfolder)
        await self.manager._ensure_dir(directory)
        legacy_name = self.manager._get_legacy_hashed_filename(filename)
        legacy_path = Path(str(directory / legacy_name))
        legacy_path.write_bytes(b"legacy")

        self.assertEqual(await self.manager.read_file(folder, subfolder, filename), b"legacy")
        await self.manager.delete_file(folder, subfolder, filename)
        self.assertFalse(legacy_path.exists())

    async def test_failed_oversize_overwrite_preserves_existing_file(self) -> None:
        folder = "customer-1"
        subfolder = "atomic"
        filename = "safe.txt"
        await self.manager.save_file(
            file=self.upload(filename, b"original"),
            folder=folder,
            subfolder=subfolder,
        )

        settings.MAX_FILE_SIZE_MB = 0
        with self.assertRaises(FileSizeError):
            await self.manager.save_file(
                file=self.upload(filename, b"too large"),
                folder=folder,
                subfolder=subfolder,
                overwrite=True,
            )

        self.assertEqual(await self.manager.read_file(folder, subfolder, filename), b"original")

    async def test_path_like_filename_is_rejected(self) -> None:
        with self.assertRaises(InvalidFileNameError):
            await self.manager.save_file(
                file=self.upload("../escape.txt", b"nope"),
                folder="customer-1",
                subfolder="project-1",
            )
