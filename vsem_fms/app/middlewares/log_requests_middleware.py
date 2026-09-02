from time import perf_counter
from typing import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response
from loguru import logger

REQUEST_ID_HEADER = "X-Request-ID"
_MAX_REQUEST_ID_LENGTH = 128


def _resolve_request_id(request: Request) -> str:
    """Return a usable client request ID or generate a new UUID."""
    request_id = request.headers.get(REQUEST_ID_HEADER, "").strip()
    if request_id and len(request_id) <= _MAX_REQUEST_ID_LENGTH:
        return request_id
    return str(uuid4())


async def log_requests_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Trace each HTTP request and emit a structured completion log."""
    request_id = _resolve_request_id(request)
    started_at = perf_counter()
    client_ip = request.client.host if request.client else None

    request.state.request_id = request_id

    with logger.contextualize(request_id=request_id):
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((perf_counter() - started_at) * 1000, 3)
            logger.bind(
                http_method=request.method,
                http_path=request.url.path,
                status_code=500,
                duration_ms=duration_ms,
                client_ip=client_ip,
            ).exception("HTTP request failed")
            raise

        duration_ms = round((perf_counter() - started_at) * 1000, 3)
        response.headers[REQUEST_ID_HEADER] = request_id
        content_length = response.headers.get("content-length")
        response_size = int(content_length) if content_length and content_length.isdigit() else None
        logger.bind(
            http_method=request.method,
            http_path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            response_size=response_size,
            client_ip=client_ip,
        ).info("HTTP request completed")
        return response
