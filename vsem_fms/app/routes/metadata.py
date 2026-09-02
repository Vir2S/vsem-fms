from email.utils import format_datetime
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from vsem_fms.app.core.auth import get_api_key
from vsem_fms.app.exceptions.file_exceptions import FileNotFound, FolderNotFoundError, InvalidFileNameError
from vsem_fms.app.schemas.file_metadata import FileMetadata, FileMetadataList
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
    response_model=FileMetadataList,
    dependencies=[Depends(get_api_key)],
    summary="List file metadata",
    description="Retrieve size, content type, modification time, and SHA-256 for files in a folder.",
)
async def list_metadata(
    file_service: Annotated[FileService, Depends(FileService)],
    folder: str,
    subfolder: str,
) -> FileMetadataList:
    try:
        files = await file_service.list_file_metadata(folder=folder, subfolder=subfolder)
        return FileMetadataList(files=[FileMetadata.model_validate(item) for item in files])
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
