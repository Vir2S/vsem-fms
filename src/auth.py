from fastapi import Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

from config import settings

# Define the API key header name
API_KEY_NAME = "X-API-Key"

# Create an API key header dependency
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)


async def get_api_key(api_key: str = Security(api_key_header)):
    """
    Validates the API key provided in the request header.

    :param api_key: API key extracted from the request headers.
    :return: The valid API key.
    :raises HTTPException: If the API key is missing or incorrect.
    """
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key",
        )
    return api_key
