import hashlib
from pathlib import Path

from vsem_fms.app.config import settings


def upload(client, filename: str, content: bytes, *, overwrite: bool = True):
    return client.post(
        "/api/v1/files",
        data={"folder": "user-1", "subfolder": "project-1", "overwrite": str(overwrite).lower()},
        files={"file": (filename, content)},
    )


def test_upload_list_get_delete_round_trip(client):
    response = upload(client, "hello.txt", b"hello world")
    assert response.status_code == 201
    assert response.json() == {
        "message": "File uploaded successfully.",
        "path": "user-1/project-1/hello.txt",
    }
    assert settings.STORAGE_PATH not in response.text

    response = client.get("/api/v1/files/user-1/project-1")
    assert response.status_code == 200
    assert response.json() == {"files": ["hello.txt"]}
    assert settings.STORAGE_PATH not in response.text

    response = client.get("/api/v1/files/user-1/project-1/hello.txt")
    assert response.status_code == 200
    assert response.json() == {"filename": "hello.txt", "content": "hello world"}

    response = client.delete("/api/v1/files/user-1/project-1/hello.txt")
    assert response.status_code == 204

    response = client.get("/api/v1/files/user-1/project-1/hello.txt")
    assert response.status_code == 404


def test_failed_oversized_overwrite_preserves_existing_file(client, monkeypatch):
    assert upload(client, "important.txt", b"original").status_code == 201
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_MB", 1)

    oversized = b"x" * (1024 * 1024 + 1)
    response = upload(client, "important.txt", oversized, overwrite=True)

    assert response.status_code == 400
    assert "allowed limit of 1.0MB" in response.json()["detail"]

    response = client.get("/api/v1/files/user-1/project-1/important.txt")
    assert response.status_code == 200
    assert response.json()["content"] == "original"


def test_overwrite_false_returns_conflict_and_preserves_file(client):
    assert upload(client, "same.txt", b"first").status_code == 201

    response = upload(client, "same.txt", b"second", overwrite=False)
    assert response.status_code == 409

    response = client.get("/api/v1/files/user-1/project-1/same.txt")
    assert response.json()["content"] == "first"


def test_unknown_binary_extension_is_downloadable(client):
    payload = b"\x00\x01\x02\xff"
    assert upload(client, "blob.unknownext", payload).status_code == 201

    response = client.get("/api/v1/files/user-1/project-1/blob.unknownext")
    assert response.status_code == 200
    assert response.content == payload
    assert response.headers["content-type"] == "application/octet-stream"
    assert "attachment" in response.headers["content-disposition"]


def test_legacy_hashed_file_can_be_read_and_deleted(client):
    folder = "user-1"
    subfolder = "project-1"
    filename = "legacy.txt"
    folder_hash = hashlib.sha256(folder.encode()).hexdigest()
    subfolder_hash = hashlib.sha256(subfolder.encode()).hexdigest()
    filename_hash = hashlib.sha256(filename.encode()).hexdigest() + ".txt"

    legacy_dir = Path(settings.STORAGE_PATH) / folder_hash / subfolder_hash
    legacy_dir.mkdir(parents=True)
    (legacy_dir / filename_hash).write_text("legacy content", encoding="utf-8")

    response = client.get(f"/api/v1/files/{folder}/{subfolder}/{filename}")
    assert response.status_code == 200
    assert response.json()["content"] == "legacy content"

    response = client.delete(f"/api/v1/files/{folder}/{subfolder}/{filename}")
    assert response.status_code == 204
    assert not (legacy_dir / filename_hash).exists()


def test_invalid_api_key_is_rejected(client):
    response = client.get(
        "/api/v1/ping",
        headers={"X-API-Key": "wrong-key"},
    )
    # Ping is intentionally public; protected endpoint must reject invalid keys.
    assert response.status_code == 200

    response = client.get(
        "/api/v1/files/user-1/project-1",
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 403


def test_upload_rejects_non_routeable_folder_segments(client):
    response = client.post(
        "/api/v1/files",
        data={"folder": "nested/folder", "subfolder": "project-1", "overwrite": "true"},
        files={"file": ("hello.txt", b"hello")},
    )
    assert response.status_code == 422


def test_upload_rejects_reserved_and_blank_folder_segments(client):
    invalid_segments = (".", "..", "   ")

    for segment in invalid_segments:
        response = client.post(
            "/api/v1/files",
            data={"folder": segment, "subfolder": "project-1", "overwrite": "true"},
            files={"file": ("hello.txt", b"hello")},
        )
        assert response.status_code == 422, segment

        response = client.post(
            "/api/v1/files",
            data={"folder": "user-1", "subfolder": segment, "overwrite": "true"},
            files={"file": ("hello.txt", b"hello")},
        )
        assert response.status_code == 422, segment


def test_insufficient_disk_space_returns_507_and_preserves_existing_file(client, monkeypatch):
    from types import SimpleNamespace
    from vsem_fms.app.core import async_fs

    assert upload(client, "important.txt", b"original").status_code == 201
    monkeypatch.setattr(settings, "MIN_FREE_DISK_SPACE_MB", 1)
    monkeypatch.setattr(
        async_fs.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(total=1024 * 1024, used=1024 * 1024, free=0),
    )

    response = upload(client, "important.txt", b"replacement", overwrite=True)
    assert response.status_code == 507

    monkeypatch.setattr(settings, "MIN_FREE_DISK_SPACE_MB", 0)
    response = client.get("/api/v1/files/user-1/project-1/important.txt")
    assert response.status_code == 200
    assert response.json()["content"] == "original"


def test_file_metadata_api_and_head(client):
    payload = b"metadata payload"
    assert upload(client, "report.pdf", payload).status_code == 201

    response = client.get("/api/v1/files/user-1/project-1/report.pdf/metadata")
    assert response.status_code == 200
    metadata = response.json()
    assert metadata["filename"] == "report.pdf"
    assert metadata["size"] == len(payload)
    assert metadata["content_type"] == "application/pdf"
    assert metadata["sha256"] == hashlib.sha256(payload).hexdigest()
    assert metadata["modified_at"].endswith("Z")

    response = client.head("/api/v1/files/user-1/project-1/report.pdf")
    assert response.status_code == 200
    assert response.content == b""
    assert response.headers["content-length"] == str(len(payload))
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["x-checksum-sha256"] == hashlib.sha256(payload).hexdigest()
    assert response.headers["etag"] == f'"sha256:{hashlib.sha256(payload).hexdigest()}"'
    assert "last-modified" in response.headers


def test_metadata_listing_is_additive_and_does_not_break_name_listing(client):
    assert upload(client, "a.txt", b"alpha").status_code == 201
    assert upload(client, "b.bin", b"\x00\x01").status_code == 201

    response = client.get("/api/v1/files/user-1/project-1")
    assert response.status_code == 200
    assert response.json() == {"files": ["a.txt", "b.bin"]}

    response = client.get("/api/v1/files/user-1/project-1/metadata")
    assert response.status_code == 200
    files = response.json()["files"]
    assert [item["filename"] for item in files] == ["a.txt", "b.bin"]
    assert files[0]["size"] == 5
    assert files[0]["content_type"] == "text/plain"
    assert files[0]["sha256"] == hashlib.sha256(b"alpha").hexdigest()
    assert files[1]["content_type"] == "application/octet-stream"


def test_metadata_endpoints_return_404_for_missing_file(client):
    response = client.get("/api/v1/files/user-1/project-1/missing.txt/metadata")
    assert response.status_code == 404

    response = client.head("/api/v1/files/user-1/project-1/missing.txt")
    assert response.status_code == 404


def test_request_id_is_generated_and_returned(client):
    from uuid import UUID

    response = client.get("/api/v1/ping")

    assert response.status_code == 200
    request_id = response.headers["x-request-id"]
    assert str(UUID(request_id)) == request_id


def test_client_request_id_is_preserved_and_added_to_structured_log(client):
    import json

    from loguru import logger

    captured: list[str] = []
    sink_id = logger.add(captured.append, serialize=True)
    try:
        response = client.get(
            "/api/v1/ping",
            headers={"X-Request-ID": "edge-request-123"},
        )
    finally:
        logger.remove(sink_id)

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "edge-request-123"

    events = [json.loads(item)["record"] for item in captured]
    completion = next(event for event in events if event["message"] == "HTTP request completed")
    assert completion["extra"]["request_id"] == "edge-request-123"
    assert completion["extra"]["http_method"] == "GET"
    assert completion["extra"]["http_path"] == "/api/v1/ping"
    assert completion["extra"]["status_code"] == 200
    assert completion["extra"]["duration_ms"] >= 0
    assert completion["extra"]["response_size"] is not None
    assert "client_ip" in completion["extra"]


def test_invalid_oversized_request_id_is_replaced(client):
    from uuid import UUID

    response = client.get(
        "/api/v1/ping",
        headers={"X-Request-ID": "x" * 129},
    )

    assert response.status_code == 200
    request_id = response.headers["x-request-id"]
    assert request_id != "x" * 129
    assert str(UUID(request_id)) == request_id


def test_request_id_propagates_to_application_logs(client):
    import json

    from loguru import logger

    captured: list[str] = []
    sink_id = logger.add(captured.append, serialize=True)
    try:
        response = client.post(
            "/api/v1/files",
            headers={"X-Request-ID": "upload-trace-456"},
            data={"folder": "user-1", "subfolder": "project-1", "overwrite": "true"},
            files={"file": ("trace.txt", b"trace me")},
        )
    finally:
        logger.remove(sink_id)

    assert response.status_code == 201
    events = [json.loads(item)["record"] for item in captured]
    saved = next(event for event in events if event["message"] == "File saved successfully: 'trace.txt'")
    assert saved["extra"]["request_id"] == "upload-trace-456"
