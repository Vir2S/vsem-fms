from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from loguru import logger

from vsem_fms.app.core.api_keys import APIPrincipal, APIScope
from vsem_fms.app.core.auth import authorize_folder_access, require_scope
from vsem_fms.app.exceptions.file_exceptions import (
    FileNotFound,
    FolderNotFoundError,
    InvalidFileEncodingError,
    InvalidFileNameError,
)
from vsem_fms.app.services.file_service import FileService


router = APIRouter(prefix="/files", tags=["Files"])


@router.get(
    "/{folder}/{subfolder}/{filename}",
    status_code=status.HTTP_200_OK,
    summary="Get file content",
    description=(
        "Retrieve a file. Supported UTF-8 text files are returned as JSON; "
        "all other files are streamed as downloads."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"description": "Forbidden"},
        status.HTTP_404_NOT_FOUND: {"description": "File or folder not found"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid filename or text encoding"},
    },
)
async def get_file(
    principal: Annotated[APIPrincipal, Depends(require_scope(APIScope.FILES_READ))],
    file_service: Annotated[FileService, Depends(FileService)],
    folder: str,
    subfolder: str,
    filename: str,
) -> Response:
    authorize_folder_access(principal, APIScope.FILES_READ, folder=folder, subfolder=subfolder)
    try:
        return await file_service.prepare_response(folder=folder, subfolder=subfolder, filename=filename)
    except (FileNotFound, FolderNotFoundError) as exc:
        logger.warning("File or folder not found: '{}'", filename)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from exc
    except (InvalidFileEncodingError, InvalidFileNameError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
