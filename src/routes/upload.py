from fastapi import APIRouter, Depends, File, UploadFile

from core.auth import get_api_key
from core.async_fs import AsyncFileManager
from core.logging import logger


file_manager = AsyncFileManager()

router = APIRouter(tags=["Files"])


@router.post("/upload")
async def upload_file(
        file: UploadFile = File(...), api_key: str = Depends(get_api_key)
):
    """
    Uploads a file asynchronously.

    :param file: Uploaded file object.
    :param api_key: API key for authentication.
    :return: JSON response with the saved file path.
    """
    file_path = await file_manager.write_file_stream(file.filename, file)
    logger.info(f"Uploaded file {file_path}")
    return {"message": "✅ File saved successfully", "path": file_path}
