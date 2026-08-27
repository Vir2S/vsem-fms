import secrets
from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from loguru import logger

from vsem_fms.app.config import settings


# Define the API key header name
API_KEY_NAME = "X-API-Key"

# Create an API key header dependency
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)


async def get_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Validate the API key provided in the request header.

    Args:
        api_key (str): The API key extracted from the request header.

    Returns:
        str: The valid API key if authentication is successful.

    Raises:
        HTTPException: If the API key is missing or invalid, a 403 Forbidden error is raised.
    """
    if not secrets.compare_digest(api_key, settings.API_KEY):
        logger.warning("❌ Invalid API Key attempt.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key",
        )

    logger.info("🔐 Valid API Key provided.")
    return api_key
