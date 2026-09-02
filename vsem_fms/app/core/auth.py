from __future__ import annotations

import secrets

from typing import Annotated, Awaitable, Callable

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security.api_key import APIKeyHeader
from loguru import logger

from vsem_fms.app.config import settings
from vsem_fms.app.core.api_keys import APIPrincipal, APIScope, hash_api_key


API_KEY_NAME = "X-API-Key"
_MAX_API_KEY_LENGTH = 1024
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or inactive API key",
        headers={"WWW-Authenticate": "ApiKey"},
    )


def _authenticate(api_key: str) -> APIPrincipal:
    digest = hash_api_key(api_key)
    legacy_api_key = settings.API_KEY
    if legacy_api_key is not None and secrets.compare_digest(digest, hash_api_key(legacy_api_key)):
        return APIPrincipal(
            id="legacy-admin",
            name="Legacy API key",
            scopes=frozenset({APIScope.ADMIN}),
            legacy=True,
        )

    for configured_key in settings.API_KEYS:
        if not secrets.compare_digest(digest, configured_key.secret_hash):
            continue
        if not configured_key.enabled:
            raise _unauthorized()
        return APIPrincipal(
            id=configured_key.id,
            name=configured_key.name,
            scopes=frozenset(configured_key.scopes),
            folder_prefix=configured_key.folder_prefix,
        )

    raise _unauthorized()


async def get_api_principal(
    request: Request,
    api_key: str | None = Security(api_key_header),
) -> APIPrincipal:
    """Authenticate an API key and attach its client identity to the request."""
    if api_key is None or not api_key or len(api_key) > _MAX_API_KEY_LENGTH:
        logger.warning("Missing or invalid API key")
        raise _unauthorized()

    try:
        principal = _authenticate(api_key)
    except HTTPException:
        logger.warning("Invalid or inactive API key attempt")
        raise

    request.state.api_client_id = principal.id
    request.state.api_client_name = principal.name
    return principal


def _is_path_allowed(principal: APIPrincipal, folder: str, subfolder: str) -> bool:
    prefix = principal.folder_prefix
    if prefix is None:
        return True

    parts = prefix.split("/")
    if len(parts) == 1:
        return secrets.compare_digest(folder, parts[0])
    return secrets.compare_digest(folder, parts[0]) and secrets.compare_digest(subfolder, parts[1])


def _forbidden(
    principal: APIPrincipal,
    *,
    required_scope: APIScope,
    folder: str | None = None,
    subfolder: str | None = None,
) -> HTTPException:
    logger.bind(
        api_client_id=principal.id,
        api_client_name=principal.name,
        required_scope=required_scope.value,
        folder=folder,
        subfolder=subfolder,
    ).warning("API client access denied")
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="API key is not authorized for this operation",
    )


def require_scope(required_scope: APIScope) -> Callable[..., Awaitable[APIPrincipal]]:
    """Build a FastAPI dependency that rejects missing operation scopes early."""

    async def dependency(
        principal: Annotated[APIPrincipal, Depends(get_api_principal)],
    ) -> APIPrincipal:
        if not principal.has_scope(required_scope):
            raise _forbidden(principal, required_scope=required_scope)
        return principal

    return dependency


def authorize_folder_access(
    principal: APIPrincipal,
    required_scope: APIScope,
    *,
    folder: str,
    subfolder: str,
) -> None:
    """Enforce an authenticated key's optional logical-folder restriction."""
    if not _is_path_allowed(principal, folder, subfolder):
        raise _forbidden(
            principal,
            required_scope=required_scope,
            folder=folder,
            subfolder=subfolder,
        )
