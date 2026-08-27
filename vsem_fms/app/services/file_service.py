import io
import os
from typing import Annotated
from urllib.parse import quote

from fastapi import Depends, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from loguru import logger

from vsem_fms.app.constants import BINARY_EXTENSIONS, MEDIA_TYPES, TEXT_EXTENSIONS
from vsem_fms.app.core.async_fs import AsyncFileManager
from vsem_fms.app.exceptions.file_exceptions import (
    FileAlreadyExistsError,
    FileNotFound,
    FileSizeError,
    FileWriteError,
    FolderNotFoundError,
    InvalidFileEncodingError,
    InvalidFileNameError,
    UnsupportedFileTypeError,
)
from vsem_fms.app.schemas.upload_schemas import UploadRequest


class FileService:
    """Service layer for file operations."""

    def __init__(self, file_manager: Annotated[AsyncFileManager, Depends(AsyncFileManager)]):
        self.file_manager = file_manager

    async def upload_file(self, file: UploadFile, upload_data: UploadRequest) -> str:
        """Validate and persist an uploaded file."""
        filename = file.filename or ""
        try:
            await self.file_manager.save_file(file=file, **upload_data.model_dump())
            return f"{upload_data.folder}/{upload_data.subfolder}/{filename}"
        except FileExistsError:
            logger.warning(f"⚠️ Upload aborted — file already exists: '{filename}'")
            raise FileAlreadyExistsError(file_name=filename)
        except (FileSizeError, InvalidFileNameError):
            raise
        except OSError as exc:
            logger.error(
                f"❌ Failed to write file '{filename}'. "
                f"Error: {exc}. Upload data: {upload_data.model_dump()}"
            )
            raise FileWriteError(path=filename) from exc

    async def list_files(self, folder: str, subfolder: str) -> list[str]:
        """Return stored filenames for a logical folder/subfolder."""
        return await self.file_manager.list_files(folder=folder, subfolder=subfolder)

    async def read_file(self, folder: str, subfolder: str, file_name: str) -> bytes:
        """Read a stored file."""
        try:
            content = await self.file_manager.read_file(
                folder=folder,
                subfolder=subfolder,
                filename=file_name,
            )
            logger.info(f"✅ File {file_name} read successfully.")
            return content
        except FileNotFoundError as exc:
            logger.error(f"❌ File not found: {file_name} in {folder}/{subfolder}")
            raise FileNotFound(folder=folder, subfolder=subfolder, file_name=file_name) from exc

    def prepare_response(self, filename: str, content: bytes) -> JSONResponse | StreamingResponse:
        """Build a JSON response for text or a streamed attachment for binary files."""
        extension = os.path.splitext(filename)[1].lower()

        if extension in TEXT_EXTENSIONS:
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError as exc:
                logger.error(f"❌ Invalid UTF-8 encoding in file: {filename}")
                raise InvalidFileEncodingError() from exc
            return JSONResponse({"filename": filename, "content": text})

        if extension in BINARY_EXTENSIONS:
            media_type = MEDIA_TYPES.get(extension, "application/octet-stream")
            encoded_filename = quote(filename)
            return StreamingResponse(
                io.BytesIO(content),
                media_type=media_type,
                headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
            )

        logger.error(f"❌ Unsupported file type: {extension} for file {filename}")
        raise UnsupportedFileTypeError(f"Unsupported file type: {extension}")

    async def delete_file(self, folder: str, subfolder: str, filename: str) -> None:
        """Delete a stored file."""
        try:
            await self.file_manager.delete_file(
                folder=folder,
                subfolder=subfolder,
                filename=filename,
            )
            logger.info(f"🗑️ File deleted: {folder}/{subfolder}/{filename}")
        except FileNotFoundError as exc:
            logger.error(f"❌ File not found: {filename} in {folder}/{subfolder}")
            raise FileNotFound(folder=folder, subfolder=subfolder, file_name=filename) from exc

