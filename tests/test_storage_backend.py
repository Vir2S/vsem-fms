from unittest.mock import AsyncMock

import pytest

from vsem_fms.app.services.file_service import FileService
from vsem_fms.app.storage.base import StorageBackend, StorageDownload
from vsem_fms.app.storage.dependencies import get_storage_backend
from vsem_fms.app.storage.local import LocalStorageBackend


def test_default_storage_backend_is_local():
    assert isinstance(get_storage_backend(), LocalStorageBackend)


@pytest.mark.anyio
async def test_file_service_depends_on_storage_contract_not_local_filesystem():
    backend = AsyncMock(spec=StorageBackend)
    backend.list_files.return_value = ["a.txt", "b.txt"]

    service = FileService(storage_backend=backend)

    assert await service.list_files("tenant", "project") == ["a.txt", "b.txt"]
    backend.list_files.assert_awaited_once_with(folder="tenant", subfolder="project")


@pytest.mark.anyio
async def test_file_service_can_stream_from_non_local_backend():
    async def chunks():
        yield b"remote-"
        yield b"content"

    backend = AsyncMock(spec=StorageBackend)
    backend.get_download.return_value = StorageDownload(
        filename="remote.bin",
        content_type="application/octet-stream",
        size=14,
        stream=chunks(),
    )
    service = FileService(storage_backend=backend)

    response = await service.prepare_response("tenant", "project", "remote.bin")

    assert response.media_type == "application/octet-stream"
    assert response.headers["content-length"] == "14"
    assert "remote.bin" in response.headers["content-disposition"]
    body = b"".join([chunk async for chunk in response.body_iterator])
    assert body == b"remote-content"


def test_configured_storage_backend_can_be_s3(monkeypatch):
    import vsem_fms.app.storage.dependencies as dependencies

    sentinel = object()
    monkeypatch.setattr(dependencies.settings, "STORAGE_BACKEND", "s3")
    monkeypatch.setattr(dependencies, "S3StorageBackend", lambda: sentinel)

    assert dependencies.get_storage_backend() is sentinel
