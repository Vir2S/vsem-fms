from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from vsem_fms.app.core.auth import get_api_key
from vsem_fms.app.core.pagination import MAX_PAGE_SIZE
from vsem_fms.app.exceptions.file_exceptions import FolderNotFoundError, InvalidCursorError
from vsem_fms.app.schemas.pagination import FileNameList, FileNamePage
from vsem_fms.app.services.file_service import FileService


router = APIRouter(prefix="/files", tags=["Files"])


@router.get(
    "/{folder}/{subfolder}",
    response_model=FileNamePage | FileNameList,
    dependencies=[Depends(get_api_key)],
    status_code=status.HTTP_200_OK,
    summary="List stored files",
    description=(
        "Retrieve files from the specified folder and subfolder. "
        "Without pagination query parameters the legacy filename-only response is preserved."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid pagination cursor"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"description": "Forbidden"},
        status.HTTP_404_NOT_FOUND: {"description": "Folder not found"},
    },
)
async def get_files_list(
    file_service: Annotated[FileService, Depends(FileService)],
    folder: str,
    subfolder: str,
    limit: Annotated[
        int | None,
        Query(ge=1, le=MAX_PAGE_SIZE, description="Page size. Supplying it enables cursor pagination."),
    ] = None,
    cursor: Annotated[
        str | None,
        Query(min_length=1, max_length=2048, description="Opaque cursor returned by the previous page."),
    ] = None,
) -> FileNamePage | FileNameList:
    """List stored logical filenames, optionally using cursor pagination."""
    try:
        if limit is None and cursor is None:
            files = await file_service.list_files(folder=folder, subfolder=subfolder)
            return FileNameList(files=files)
        else:
            content = await file_service.list_files_page(
                folder=folder,
                subfolder=subfolder,
                limit=limit,
                cursor=cursor,
            )
            return FileNamePage.model_validate(content)
    except InvalidCursorError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    except FolderNotFoundError as exc:
        logger.error("Folder listing failed: folder='{}' subfolder='{}' not found", folder, subfolder)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from exc
