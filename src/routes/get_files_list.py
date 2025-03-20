from fastapi import APIRouter, Depends, HTTPException, status

from core.auth import get_api_key
from core.async_fs import AsyncFileManager
from core.logging import logger


file_manager = AsyncFileManager()

router = APIRouter(tags=["Files"])


@router.get("/files")
async def get_files_list(api_key: str = Depends(get_api_key)):
    """
    Retrieves a list of stored files.

    :param api_key: API key for authentication.
    :return: JSON response with a list of file paths.
    """
    files = await file_manager.list_files()
    logger.info(f"Found {len(files)} files")
    return {"files": files}
