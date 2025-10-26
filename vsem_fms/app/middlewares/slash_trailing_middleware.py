from typing import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import RedirectResponse


async def trailing_slash_handler_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> RedirectResponse | Response:
    """
    Middleware to standardize URLs by removing trailing slashes.
    Redirects requests ending with '/' to the same URL without it.

    Args:
        request (Request): The incoming HTTP request.
        call_next (function): The next middleware or route handler.

    Returns:
        Response: Either a redirected response or the original response.
    """
    url = request.url.path
    query_string = request.url.query  # Correctly extract the query string

    if url != "/" and url.endswith("/"):  # Remove trailing slash
        new_url = url.rstrip("/")
        # Reconstruct URL with query parameters if they exist
        full_url = f"{new_url}?{query_string}" if query_string else new_url
        return RedirectResponse(url=full_url, status_code=307)

    return await call_next(request)
