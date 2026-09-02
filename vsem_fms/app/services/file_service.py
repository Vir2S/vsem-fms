import mimetypes
import os
from pathlib import PurePosixPath
from typing import Annotated

from fastapi import Depends, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from loguru import logger

from vsem_fms.app.constants import TEXT_EXTENSIONS
from vsem_fms.app.core.async_fs import AsyncFileManager
from vsem_fms.app.core.pagination import DEFAULT_PAGE_SIZE, decode_cursor, encode_cursor
from vsem_fms.app.exceptions.file_exceptions import (
    FileAlreadyExistsError,
    InvalidCursorError,
    FileNotFound,
    FileSizeError,
    FileWriteError,
    FolderNotFoundError,
    InvalidFileEncodingError,
    InvalidFileNameError,
)
from vsem_fms.app.schemas.upload_schemas import UploadRequest


class FileService:
    """Application service for file operations."""

    def __init__(self, file_manager: Annotated[AsyncFileManager, Depends(AsyncFileManager)]):
        self.file_manager = file_manager

    async def upload_file(self, file: UploadFile, upload_data: UploadRequest) -> str:
        """Validate and save a file, returning only its logical API path."""
        try:
            await self.file_manager.save_file(file=file, **upload_data.model_dump())
        except FileExistsError as exc:
            raise FileAlreadyExistsError(file_name=file.filename or "") from exc
        except FileSizeError:
            raise
        except ValueError as exc:
            raise InvalidFileNameError(file_name=file.filename) from exc
        except OSError as exc:
            logger.exception("Failed to write file '{}'", file.filename)
            raise FileWriteError(path=file.filename or "<unknown>") from exc

        filename = file.filename or ""
        return str(PurePosixPath(upload_data.folder) / upload_data.subfolder / filename)

    async def list_files(self, folder: str, subfolder: str) -> list[str]:
        return await self.file_manager.list_files(folder=folder, subfolder=subfolder)

    @staticmethod
    def _decode_cursor(cursor: str | None) -> str | None:
        if cursor is None:
            return None
        try:
            return decode_cursor(cursor)
        except ValueError as exc:
            raise InvalidCursorError() from exc

    @staticmethod
    def _page_response(items: list[object], has_more: bool) -> dict[str, object]:
        next_cursor = encode_cursor(str(items[-1])) if has_more and items else None
        return {
            "files": items,
            "has_more": has_more,
            "next_cursor": next_cursor,
        }

    async def list_files_page(
        self,
        folder: str,
        subfolder: str,
        *,
        limit: int | None,
        cursor: str | None,
    ) -> dict[str, object]:
        """Return one cursor page while preserving the legacy unpaginated API separately."""
        after = self._decode_cursor(cursor)
        files, has_more = await self.file_manager.list_files_page(
            folder=folder,
            subfolder=subfolder,
            limit=limit or DEFAULT_PAGE_SIZE,
            after=after,
        )
        return self._page_response(files, has_more)

    async def read_file(self, folder: str, subfolder: str, file_name: str) -> bytes:
        try:
            return await self.file_manager.read_file(folder=folder, subfolder=subfolder, filename=file_name)
        except FileNotFoundError as exc:
            raise FileNotFound(folder=folder, subfolder=subfolder, file_name=file_name) from exc

    async def prepare_response(self, folder: str, subfolder: str, filename: str) -> Response:
        """Return inline JSON for UTF-8 text and true streamed responses for all other files."""
        extension = os.path.splitext(filename)[1].lower()

        try:
            file_path = await self.file_manager.get_file_path(
                folder=folder,
                subfolder=subfolder,
                filename=filename,
            )
        except FileNotFoundError as exc:
            raise FileNotFound(folder=folder, subfolder=subfolder, file_name=filename) from exc
        except ValueError as exc:
            raise InvalidFileNameError(file_name=filename) from exc

        if extension in TEXT_EXTENSIONS:
            content = await self.read_file(folder=folder, subfolder=subfolder, file_name=filename)
            try:
                return JSONResponse({"filename": filename, "content": content.decode("utf-8")})
            except UnicodeDecodeError as exc:
                raise InvalidFileEncodingError() from exc

        media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=filename,
        )


    async def get_file_metadata(self, folder: str, subfolder: str, filename: str) -> dict[str, object]:
        """Return public metadata for one logical file."""
        try:
            return await self.file_manager.get_file_metadata(
                folder=folder,
                subfolder=subfolder,
                filename=filename,
            )
        except FileNotFoundError as exc:
            raise FileNotFound(folder=folder, subfolder=subfolder, file_name=filename) from exc
        except ValueError as exc:
            raise InvalidFileNameError(file_name=filename) from exc

    async def list_file_metadata(self, folder: str, subfolder: str) -> list[dict[str, object]]:
        """Return public metadata for all listable files in a logical folder."""
        return await self.file_manager.list_file_metadata(folder=folder, subfolder=subfolder)

    async def list_file_metadata_page(
        self,
        folder: str,
        subfolder: str,
        *,
        limit: int | None,
        cursor: str | None,
    ) -> dict[str, object]:
        """Return one metadata page and compute checksums only for that page."""
        after = self._decode_cursor(cursor)
        files, has_more = await self.file_manager.list_file_metadata_page(
            folder=folder,
            subfolder=subfolder,
            limit=limit or DEFAULT_PAGE_SIZE,
            after=after,
        )
        next_cursor = encode_cursor(str(files[-1]["filename"])) if has_more and files else None
        return {
            "files": files,
            "has_more": has_more,
            "next_cursor": next_cursor,
        }

    async def delete_file(self, folder: str, subfolder: str, filename: str) -> None:
        try:
            await self.file_manager.delete_file(folder=folder, subfolder=subfolder, filename=filename)
        except FileNotFoundError as exc:
            raise FileNotFound(folder=folder, subfolder=subfolder, file_name=filename) from exc
        except ValueError as exc:
            raise InvalidFileNameError(file_name=filename) from exc
