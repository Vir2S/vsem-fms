from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from loguru import logger

from vsem_fms.app.core.auth import get_api_key
from vsem_fms.app.exceptions.file_exceptions import FileNotFound, FolderNotFoundError
from vsem_fms.app.services.file_service import FileService


router = APIRouter(prefix="/files", tags=["Files"])


@router.delete(
    "/{folder}/{subfolder}/{filename}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_api_key)],
    summary="Delete a file",
    description="This endpoint deletes a file by filename from the server.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"description": "Forbidden"},
        status.HTTP_404_NOT_FOUND: {"description": "File not found"},
    },
)
async def delete_file(
    file_service: Annotated[FileService, Depends(FileService)], folder: str, subfolder: str, filename: str
) -> Response:
    """
    Delete a file from the server.

    Args:
        file_service (FileService): The file service used for file operations.
        folder (str): The name of the parent directory.
        subfolder (str): The name of the subdirectory.
        filename (str): The name of the file to delete.

    Returns:
        Response: A confirmation of successful deletion or an error message.

    Raises:
        HTTPException: Raised if the file or folder is not found.
    """
    try:
        await file_service.delete_file(folder=folder, subfolder=subfolder, filename=filename)

        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except (FileNotFound, FolderNotFoundError) as e:
        logger.warning(f"❌ Failed to retrieve file '{filename}' from {folder}/{subfolder}: {e.detail}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
