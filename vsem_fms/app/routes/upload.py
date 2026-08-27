from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from loguru import logger

from vsem_fms.app.core.auth import get_api_key
from vsem_fms.app.exceptions.file_exceptions import (
    FileAlreadyExistsError,
    FileSizeError,
    FileWriteError,
    InvalidFileNameError,
)
from vsem_fms.app.schemas.upload_schemas import UploadRequest, UploadResponse
from vsem_fms.app.services.file_service import FileService


router = APIRouter(prefix="/files", tags=["Files"])


@router.post(
    "",
    summary="Upload a file",
    description="Upload a file to the server and save it to the specified folder.",
    response_model=UploadResponse,
    dependencies=[Depends(get_api_key)],
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid request or error during upload."},
        409: {"description": "File already exists."},
        422: {"description": "Validation error on the input data."},
        500: {"description": "File write error."},
    },
)
async def upload_model(
    file_service: Annotated[FileService, Depends(FileService)],
    upload_request: Annotated[UploadRequest, Depends(UploadRequest.as_form)],
    file: Annotated[UploadFile, File(description="The file to be uploaded")],
) -> UploadResponse:
    """
    Upload a file to the server and save it to the appropriate folder and subfolder.

    Args:
        file_service (FileService): The file service used to handle file upload.
        file (UploadFile): The file to be uploaded.
        upload_request (UploadRequest): The request data containing folder, subfolder, and other upload details.

    Returns:
        UploadResponse: A response containing a success message and the path to the uploaded file.

    Raises:
        HTTPException: If any errors occur during the upload process, such as:
            - 409 Conflict: If the file already exists and cannot be overwritten.
            - 400 Bad Request: If the file size exceeds the allowed limit.
            - 500 Internal Server Error: For storage write failures or other internal upload errors.
    """
    try:
        saved_path = await file_service.upload_file(file=file, upload_data=upload_request)

        return UploadResponse(
            message="File uploaded successfully.",
            path=saved_path,
        )

    except FileAlreadyExistsError as e:
        logger.warning(f"Upload failed: file already exists '{file.filename}'")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.detail)

    except FileSizeError as e:
        logger.warning(f"Upload failed: file size error '{file.filename}'")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.detail)

    except InvalidFileNameError as e:
        logger.warning(f"Upload failed: invalid filename '{file.filename}'")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.detail)

    except FileWriteError as e:
        logger.error(f"Upload failed: internal error with file '{file.filename}': {e.detail}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.detail)
