from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from vsem_fms.app.core.api_keys import APIPrincipal, APIScope
from vsem_fms.app.core.auth import authorize_folder_access, require_scope
from vsem_fms.app.exceptions.file_exceptions import (
    FileAlreadyExistsError,
    FileSizeError,
    FileWriteError,
    InvalidFileNameError,
    InsufficientStorageError,
)
from vsem_fms.app.schemas.upload_schemas import UploadRequest, UploadResponse
from vsem_fms.app.services.file_service import FileService


router = APIRouter(prefix="/files", tags=["Files"])


@router.post(
    "",
    summary="Upload a file",
    description="Upload a file to the specified logical folder and subfolder.",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        400: {"description": "Invalid filename or file exceeds size limit."},
        409: {"description": "File already exists."},
        507: {"description": "Insufficient storage space."},
        422: {"description": "Validation error."},
        500: {"description": "File write error."},
    },
)
async def upload_file(
    principal: Annotated[APIPrincipal, Depends(require_scope(APIScope.FILES_WRITE))],
    file_service: Annotated[FileService, Depends(FileService)],
    upload_request: Annotated[UploadRequest, Depends(UploadRequest.as_form)],
    file: Annotated[UploadFile, File(description="The file to upload")],
) -> UploadResponse:
    authorize_folder_access(
        principal,
        APIScope.FILES_WRITE,
        folder=upload_request.folder,
        subfolder=upload_request.subfolder,
    )
    try:
        saved_path = await file_service.upload_file(file=file, upload_data=upload_request)
        return UploadResponse(message="File uploaded successfully.", path=saved_path)
    except (FileSizeError, InvalidFileNameError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    except FileAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc
    except InsufficientStorageError as exc:
        raise HTTPException(status_code=status.HTTP_507_INSUFFICIENT_STORAGE, detail=exc.detail) from exc
    except FileWriteError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.detail) from exc
