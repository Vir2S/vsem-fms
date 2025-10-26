from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from starlette.responses import JSONResponse

from vsem_fms.app.core.auth import get_api_key
from vsem_fms.app.exceptions.file_exceptions import FolderNotFoundError
from vsem_fms.app.services.file_service import FileService


router = APIRouter(prefix="/files", tags=["Files"])


@router.get(
    "/{folder}/{subfolder}",
    dependencies=[Depends(get_api_key)],
    status_code=status.HTTP_200_OK,
    summary="List stored files",
    description="Retrieve a list of files from the specified folder and subfolder.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"description": "Forbidden"},
        status.HTTP_404_NOT_FOUND: {"description": "Folder not found"},
    },
)
async def get_files_list(
    file_service: Annotated[FileService, Depends(FileService)], folder: str, subfolder: str
) -> JSONResponse:
    """
    Get a list of stored files from a folder.

    Args:
        file_service (FileService): Service to handle file operations.
        folder (str): Parent folder name.
        subfolder (str): Subfolder name.

    Returns:
        JSONResponse: A list of file names.

    Raises:
        HTTPException: 404 if the folder is not found.
    """
    try:
        files = await file_service.list_files(folder=folder, subfolder=subfolder)
        return JSONResponse(content={"files": files}, status_code=status.HTTP_200_OK)

    except FolderNotFoundError as e:
        logger.error(f"📁 API error: folder='{folder}' subfolder='{subfolder}' not found — returning 404")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
