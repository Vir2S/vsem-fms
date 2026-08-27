import secrets

from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from loguru import logger

from vsem_fms.app.config import settings


API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)


async def get_api_key(api_key: str = Security(api_key_header)) -> str:
    """Validate the API key provided in the request header."""
    if not secrets.compare_digest(api_key, settings.API_KEY):
        logger.warning("Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key",
        )

    return api_key
