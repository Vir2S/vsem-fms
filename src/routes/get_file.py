from fastapi import APIRouter, Depends, HTTPException, Response

from core.auth import get_api_key
from core.async_fs import AsyncFileManager
from core.logging import logger


file_manager = AsyncFileManager()

router = APIRouter(tags=["Files"])


@router.get("/files/{filename}")
async def get_file(filename: str, api_key: str = Depends(get_api_key)):
    """
    Retrieves the content of a specific file.

    :param filename: Name of the file to retrieve.
    :param api_key: API key for authentication.
    :return: JSON response with file content.
    :raises HTTPException: If the file is not found.
    """
    try:
        content = await file_manager.read_file(filename)
        logger.info(f"File {filename} retrieved.")
        return Response(
            {
                "filename": filename,
                "content": content.decode()
            },
            status_code=200,
        )

    except FileNotFoundError:
        logger.error(f"File {filename} not found.")
        raise HTTPException(status_code=404, detail="❌ File not found")
