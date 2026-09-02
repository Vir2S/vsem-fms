from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from loguru import logger

from vsem_fms.app.core.api_keys import APIPrincipal, APIScope
from vsem_fms.app.core.auth import authorize_folder_access, require_scope
from vsem_fms.app.exceptions.file_exceptions import FileNotFound, FolderNotFoundError, InvalidFileNameError
from vsem_fms.app.services.file_service import FileService


router = APIRouter(prefix="/files", tags=["Files"])


@router.delete(
    "/{folder}/{subfolder}/{filename}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a file",
    description="Delete a file by its original logical filename.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"description": "Forbidden"},
        status.HTTP_404_NOT_FOUND: {"description": "File or folder not found"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid filename"},
    },
)
async def delete_file(
    principal: Annotated[APIPrincipal, Depends(require_scope(APIScope.FILES_DELETE))],
    file_service: Annotated[FileService, Depends(FileService)],
    folder: str,
    subfolder: str,
    filename: str,
) -> Response:
    authorize_folder_access(principal, APIScope.FILES_DELETE, folder=folder, subfolder=subfolder)
    try:
        await file_service.delete_file(folder=folder, subfolder=subfolder, filename=filename)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except (FileNotFound, FolderNotFoundError) as exc:
        logger.warning("Failed to delete file '{}' from {}/{}", filename, folder, subfolder)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from exc
    except InvalidFileNameError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
