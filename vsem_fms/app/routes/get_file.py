from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from starlette.responses import JSONResponse

from vsem_fms.app.core.auth import get_api_key
from vsem_fms.app.exceptions.file_exceptions import (
    FileNotFound,
    FolderNotFoundError,
    InvalidFileEncodingError,
    UnsupportedFileTypeError,
)
from vsem_fms.app.services.file_service import FileService


router = APIRouter(prefix="/files", tags=["Files"])


@router.get(
    "/{folder}/{subfolder}/{filename}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_api_key)],
    summary="Get file content",
    description="Retrieve the content of a specific file from the server within a folder and subfolder.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"description": "Forbidden"},
        status.HTTP_404_NOT_FOUND: {"description": "File or folder not found"},
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {"description": "Unsupported file type"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid file encoding"},
    },
)
async def get_file(
    file_service: Annotated[FileService, Depends(FileService)], folder: str, subfolder: str, filename: str
) -> JSONResponse:
    """
    Retrieve the content of a specific file from a folder and subfolder.
    This endpoint allows users to access the content of a file
    stored on the server, given its folder, subfolder, and filename.

    Args:
        file_service (FileService): The service instance for handling file operations.
        folder (str): The name of the folder containing the file.
        subfolder (str): The name of the subfolder containing the file.
        filename (str): The name of the file to retrieve.

    Returns:
        JSONResponse: A response containing the file content or an error message.
    """
    try:
        content = await file_service.read_file(folder=folder, subfolder=subfolder, file_name=filename)
        response = file_service.prepare_response(filename=filename, content=content)

        return response

    except (FileNotFound, FolderNotFoundError) as e:
        logger.warning(f"File or folder not found: {filename} in {folder}/{subfolder} - {e.detail}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)

    except InvalidFileEncodingError as e:
        logger.warning(f"Invalid encoding in file {filename}: {e.detail}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.detail)

    except UnsupportedFileTypeError as e:
        logger.warning(f"Unsupported file type for file {filename}: {e.detail}")
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=e.detail)
