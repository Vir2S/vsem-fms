import os

import pytest
from fastapi.testclient import TestClient


os.environ.setdefault("API_KEY", "test-api-key-0123456789")
os.environ.setdefault("LOG_DIR", "/tmp/vsem-fms-test-logs")

from vsem_fms.app.config import settings  # noqa: E402
from vsem_fms.app.main import app  # noqa: E402


@pytest.fixture
def api_key() -> str:
    return settings.API_KEY


@pytest.fixture
def client(tmp_path, monkeypatch, api_key):
    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_MB", 100)
    monkeypatch.setattr(settings, "MAX_FILE_AGE_HOURS", 168)

    with TestClient(app) as test_client:
        test_client.headers.update({"X-API-Key": api_key})
        yield test_client
