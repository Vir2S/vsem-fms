from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from anyio import CancelScope, to_thread
from fastapi import FastAPI, Request

from vsem_fms.app.config import settings
from vsem_fms.app.storage.base import StorageBackend
from vsem_fms.app.storage.local import LocalStorageBackend
from vsem_fms.app.storage.s3 import S3StorageBackend


def create_storage_backend() -> StorageBackend:
    """Create a backend owned by the caller."""
    if settings.STORAGE_BACKEND == "s3":
        return S3StorageBackend()
    return LocalStorageBackend()


@asynccontextmanager
async def storage_backend_context() -> AsyncIterator[StorageBackend]:
    """Own a backend for the lifetime of a server or worker."""
    backend = await to_thread.run_sync(create_storage_backend)
    try:
        yield backend
    finally:
        with CancelScope(shield=True):
            await backend.aclose()


@asynccontextmanager
async def storage_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Share one S3 backend per application lifespan, not across processes."""
    if settings.STORAGE_BACKEND != "s3":
        yield
        return

    async with storage_backend_context() as backend:
        app.state.storage_backend = backend
        try:
            yield
        finally:
            del app.state.storage_backend


def get_storage_backend(request: Request = None) -> StorageBackend:
    """Resolve shared S3 storage or keep local storage request-scoped.

    Direct calls without a request retain the factory behavior; the caller owns
    the returned backend and must close it if it has external resources.
    """
    if request is None:
        return create_storage_backend()
    if settings.STORAGE_BACKEND == "s3":
        backend = getattr(request.app.state, "storage_backend", None)
        if backend is None:
            raise RuntimeError("S3 storage requires an active application lifespan")
        return backend
    return LocalStorageBackend()
