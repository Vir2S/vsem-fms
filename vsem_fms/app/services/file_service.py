import os
from pathlib import PurePosixPath
from typing import Annotated
from urllib.parse import quote

from fastapi import Depends, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from loguru import logger

from vsem_fms.app.constants import TEXT_EXTENSIONS
from vsem_fms.app.core.pagination import DEFAULT_PAGE_SIZE, decode_cursor, encode_cursor
from vsem_fms.app.exceptions.file_exceptions import (
    FileAlreadyExistsError,
    InvalidCursorError,
    FileNotFound,
    FileSizeError,
    FileWriteError,
    InvalidFileEncodingError,
    InvalidFileNameError,
)
from vsem_fms.app.schemas.upload_schemas import UploadRequest
from vsem_fms.app.storage.base import StorageBackend, StorageDownload
from vsem_fms.app.storage.dependencies import get_storage_backend


class FileService:
    """Application service for file operations."""

    def __init__(
        self,
        storage_backend: Annotated[StorageBackend, Depends(get_storage_backend)],
    ):
        self.storage_backend = storage_backend

    async def upload_file(self, file: UploadFile, upload_data: UploadRequest) -> str:
        """Validate and save a file, returning only its logical API path."""
        try:
            await self.storage_backend.save_file(file=file, **upload_data.model_dump())
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
        return await self.storage_backend.list_files(folder=folder, subfolder=subfolder)

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
        files, has_more = await self.storage_backend.list_files_page(
            folder=folder,
            subfolder=subfolder,
            limit=limit or DEFAULT_PAGE_SIZE,
            after=after,
        )
        return self._page_response(files, has_more)

    async def read_file(self, folder: str, subfolder: str, file_name: str) -> bytes:
        try:
            return await self.storage_backend.read_file(folder=folder, subfolder=subfolder, filename=file_name)
        except FileNotFoundError as exc:
            raise FileNotFound(folder=folder, subfolder=subfolder, file_name=file_name) from exc
        except ValueError as exc:
            raise InvalidFileNameError(file_name=file_name) from exc

    async def _get_download(self, folder: str, subfolder: str, filename: str) -> StorageDownload:
        try:
            return await self.storage_backend.get_download(
                folder=folder,
                subfolder=subfolder,
                filename=filename,
            )
        except FileNotFoundError as exc:
            raise FileNotFound(folder=folder, subfolder=subfolder, file_name=filename) from exc
        except ValueError as exc:
            raise InvalidFileNameError(file_name=filename) from exc

    async def prepare_response(self, folder: str, subfolder: str, filename: str) -> Response:
        """Return inline JSON for UTF-8 text and backend-neutral streamed binary responses."""
        extension = os.path.splitext(filename)[1].lower()

        if extension in TEXT_EXTENSIONS:
            content = await self.read_file(folder=folder, subfolder=subfolder, file_name=filename)
            try:
                return JSONResponse({"filename": filename, "content": content.decode("utf-8")})
            except UnicodeDecodeError as exc:
                raise InvalidFileEncodingError() from exc

        download = await self._get_download(folder=folder, subfolder=subfolder, filename=filename)
        if download.local_path is not None:
            return FileResponse(
                path=download.local_path,
                media_type=download.content_type,
                filename=download.filename,
            )

        if download.stream is not None:
            headers = {
                "Content-Disposition": f"attachment; filename*=utf-8''{quote(download.filename)}",
            }
            if download.size is not None:
                headers["Content-Length"] = str(download.size)
            return StreamingResponse(
                download.stream,
                media_type=download.content_type,
                headers=headers,
            )

        raise RuntimeError("Storage backend returned a download without a local path or stream")

    async def get_file_metadata(self, folder: str, subfolder: str, filename: str) -> dict[str, object]:
        """Return public metadata for one logical file."""
        try:
            return await self.storage_backend.get_file_metadata(
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
        return await self.storage_backend.list_file_metadata(folder=folder, subfolder=subfolder)

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
        files, has_more = await self.storage_backend.list_file_metadata_page(
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
            await self.storage_backend.delete_file(folder=folder, subfolder=subfolder, filename=filename)
        except FileNotFoundError as exc:
            raise FileNotFound(folder=folder, subfolder=subfolder, file_name=filename) from exc
        except ValueError as exc:
            raise InvalidFileNameError(file_name=filename) from exc
