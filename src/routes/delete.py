from fastapi import APIRouter, Depends, HTTPException, Response

from core.auth import get_api_key
from core.async_fs import AsyncFileManager
from core.logging import logger


file_manager = AsyncFileManager()

router = APIRouter(tags=["Files"])


@router.delete("/files/{filename}")
async def delete_file(filename: str, api_key: str = Depends(get_api_key)):
    """
    Deletes a specified file.

    :param filename: Name of the file to delete.
    :param api_key: API key for authentication.
    :return: JSON response confirming file deletion.
    :raises HTTPException: If the file does not exist.
    """
    success = await file_manager.delete_file(filename)

    if not success:
        logger.error(f"File {filename} not found.")
        raise HTTPException(status_code=404, detail="❌ File not found")

    logger.info(f"File {filename} deleted.")
    return Response(
        {
            "message": "🗑️ File deleted successfully"
        },
        status_code=204,
    )
