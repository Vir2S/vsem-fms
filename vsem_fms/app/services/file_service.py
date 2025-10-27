import io
import os
from typing import Annotated

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
    UnsupportedFileTypeError,
)
from vsem_fms.app.schemas.upload_schemas import UploadRequest


class FileService:
    """
    Service for processing operations with files.
    """

    def __init__(self, file_manager: Annotated[AsyncFileManager, Depends(AsyncFileManager)]):
        """
        Initialize the FileService with a file manager.

        Args:
            file_manager (AsyncFileManager): An instance of AsyncFileManager for handling file operations.
        """
        self.file_manager = file_manager

    async def upload_file(self, file: UploadFile, upload_data: UploadRequest) -> str:
        """
        Upload a file with validation and saving.

        Args:
            file (UploadFile): File to be uploaded.
            upload_data (UploadRequest): Data related to the upload.

        Returns:
            str: Path to the saved file.

        Raises:
            FileServiceError: Custom exceptions related to file operations.
        """
        try:
            saved_path = await self.file_manager.save_file(file=file, **upload_data.model_dump())
            return str(saved_path)

        except FileExistsError:
            logger.warning(f"⚠️ Upload aborted — file already exists: '{file.filename}'")
            raise FileAlreadyExistsError(file_name=file.filename)

        except ValueError:
            file_size = file.size
            logger.error(f"❌ File '{file.filename}' size {file_size} exceeds limit during upload")
            raise FileSizeError(size=file_size, limit=10 * 1024 * 1024)

        except IOError as e:
            logger.error(
                f"❌ IOError while writing file '{file.filename}'. "
                f"Error: {str(e)}. Upload data: {upload_data.model_dump()}"
            )
            raise FileWriteError(path=file.filename)

    async def list_files(self, folder: str, subfolder: str) -> list:
        """
        Retrieve a list of files from the specified folder and subfolder.

        Args:
            folder (str): The parent directory.
            subfolder (str): The subdirectory.

        Returns:
            list: A list of filenames in the specified directory.

        Raises:
            FolderNotFoundError: If the specified folder or subfolder does not exist.
        """
        try:
            files = await self.file_manager.list_files(folder=folder, subfolder=subfolder)
            return files

        except FolderNotFoundError as e:
            raise e

    async def read_file(self, folder: str, subfolder: str, file_name: str) -> bytes:
        """
        Retrieve the content of a file from the specified folder and subfolder.

        Args:
            folder (str): The parent directory.
            subfolder (str): The subdirectory.
            file_name (str): The name of the file to read.

        Returns:
            bytes: Content of the file.

        Raises:
            FileNotFoundError: If the specified file does not exist.
        """
        try:
            file_content = await self.file_manager.read_file(folder=folder, subfolder=subfolder, filename=file_name)
            logger.info(f"✅ File {file_name} read successfully.")
            return file_content

        except FileNotFoundError:
            logger.error(f"❌ File not found: {file_name} in {folder}/{subfolder}")
            raise FileNotFound(folder=folder, subfolder=subfolder, file_name=file_name)

        except FolderNotFoundError as e:
            logger.error(f"❌ Directory not found: {folder}/{subfolder}")
            raise e

    def prepare_response(self, filename: str, content: bytes) -> JSONResponse | StreamingResponse:
        """
        Prepares a response based on the file type and content.

        Args:
            filename (str): The name of the file.
            content (bytes): The content of the file.

        Returns:
            JSONResponse or StreamingResponse: Response containing the file content or an error message.
        """
        extension = os.path.splitext(filename)[1].lower()

        if extension in TEXT_EXTENSIONS:
            try:
                text = content.decode("utf-8")
                return JSONResponse({"filename": filename, "content": text})

            except UnicodeDecodeError:
                logger.error(f"❌ Invalid UTF-8 encoding in file: {filename}")
                raise InvalidFileEncodingError()

        elif extension in BINARY_EXTENSIONS:
            media_type = MEDIA_TYPES.get(extension, "application/octet-stream")
            return StreamingResponse(
                io.BytesIO(content),
                media_type=media_type,
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )
        else:
            logger.error(f"❌ Unsupported file type: {extension} for file {filename}")
            raise UnsupportedFileTypeError(f"Unsupported file type: {extension}")

    async def delete_file(self, folder: str, subfolder: str, filename: str) -> None:
        """
        Deletes a file using the file manager.

        Args:
            folder (str): The name of the parent directory.
            subfolder (str): The name of the subdirectory.
            filename (str): The name of the file to delete.

        Raises:
            FileNotFound: If the file does not exist.
            FolderNotFoundError: If the specified folder does not exist.
        """
        try:
            success = await self.file_manager.delete_file(folder=folder, subfolder=subfolder, filename=filename)
            if not success:
                logger.error(f"❌ File not found: {folder}/{subfolder}/{filename}")
                raise FileNotFound(folder=folder, subfolder=subfolder, file_name=filename)

            logger.info(f"🗑️ File deleted: {folder}/{subfolder}/{filename}")

        except FileNotFoundError:
            logger.error(f"❌ File not found: {filename} in {folder}/{subfolder}")
            raise FileNotFound(folder=folder, subfolder=subfolder, file_name=filename)

        except FolderNotFoundError as e:
            logger.error(f"❌ Directory not found: {folder}/{subfolder}")
            raise e
