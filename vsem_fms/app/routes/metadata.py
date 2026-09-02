from datetime import datetime
from email.utils import format_datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from vsem_fms.app.core.auth import get_api_key
from vsem_fms.app.core.pagination import MAX_PAGE_SIZE
from vsem_fms.app.exceptions.file_exceptions import (
    FileNotFound,
    FolderNotFoundError,
    InvalidCursorError,
    InvalidFileNameError,
)
from vsem_fms.app.schemas.file_metadata import FileMetadata, FileMetadataList
from vsem_fms.app.schemas.pagination import FileMetadataPage
from vsem_fms.app.services.file_service import FileService


router = APIRouter(prefix="/files", tags=["Files"])


def _metadata_headers(metadata: dict[str, object]) -> dict[str, str]:
    modified_at = datetime.fromisoformat(str(metadata["modified_at"]).replace("Z", "+00:00"))
    return {
        "Content-Length": str(metadata["size"]),
        "Content-Type": str(metadata["content_type"]),
        "Last-Modified": format_datetime(modified_at, usegmt=True),
        "ETag": f'"sha256:{metadata["sha256"]}"',
        "X-Checksum-SHA256": str(metadata["sha256"]),
    }


@router.get(
    "/{folder}/{subfolder}/metadata",
    response_model=FileMetadataPage | FileMetadataList,
    dependencies=[Depends(get_api_key)],
    summary="List file metadata",
    description=(
        "Retrieve size, content type, modification time, and SHA-256 for files in a folder. "
        "Supplying limit or cursor enables cursor pagination."
    ),
)
async def list_metadata(
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
) -> FileMetadataPage | FileMetadataList:
    try:
        if limit is None and cursor is None:
            files = await file_service.list_file_metadata(folder=folder, subfolder=subfolder)
            return FileMetadataList(files=[FileMetadata.model_validate(item) for item in files])

        page = await file_service.list_file_metadata_page(
            folder=folder,
            subfolder=subfolder,
            limit=limit,
            cursor=cursor,
        )
        return FileMetadataPage(
            files=[FileMetadata.model_validate(item) for item in page["files"]],
            has_more=bool(page["has_more"]),
            next_cursor=str(page["next_cursor"]) if page["next_cursor"] is not None else None,
        )
    except InvalidCursorError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    except FolderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from exc


@router.get(
    "/{folder}/{subfolder}/{filename}/metadata",
    response_model=FileMetadata,
    dependencies=[Depends(get_api_key)],
    summary="Get file metadata",
    description="Retrieve size, content type, modification time, and SHA-256 for a file.",
)
async def get_metadata(
    file_service: Annotated[FileService, Depends(FileService)],
    folder: str,
    subfolder: str,
    filename: str,
) -> FileMetadata:
    try:
        metadata = await file_service.get_file_metadata(folder=folder, subfolder=subfolder, filename=filename)
        return FileMetadata.model_validate(metadata)
    except (FileNotFound, FolderNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from exc
    except InvalidFileNameError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc


@router.head(
    "/{folder}/{subfolder}/{filename}",
    dependencies=[Depends(get_api_key)],
    summary="Get file headers",
    description="Retrieve file metadata as HTTP headers without returning the file body.",
)
async def head_file(
    file_service: Annotated[FileService, Depends(FileService)],
    folder: str,
    subfolder: str,
    filename: str,
) -> Response:
    try:
        metadata = await file_service.get_file_metadata(folder=folder, subfolder=subfolder, filename=filename)
        return Response(status_code=status.HTTP_200_OK, headers=_metadata_headers(metadata))
    except (FileNotFound, FolderNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from exc
    except InvalidFileNameError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
