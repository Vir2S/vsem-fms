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
    assert response.status_code == 401


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


def test_filename_listing_supports_cursor_pagination_without_breaking_legacy_response(client):
    for filename in ("a.txt", "b.txt", "c.txt", "d.txt", "e.txt"):
        assert upload(client, filename, filename.encode()).status_code == 201

    legacy = client.get("/api/v1/files/user-1/project-1")
    assert legacy.status_code == 200
    assert legacy.json() == {"files": ["a.txt", "b.txt", "c.txt", "d.txt", "e.txt"]}

    first = client.get("/api/v1/files/user-1/project-1?limit=2")
    assert first.status_code == 200
    assert first.json()["files"] == ["a.txt", "b.txt"]
    assert first.json()["has_more"] is True
    assert first.json()["next_cursor"]

    second = client.get(
        "/api/v1/files/user-1/project-1",
        params={"limit": 2, "cursor": first.json()["next_cursor"]},
    )
    assert second.status_code == 200
    assert second.json()["files"] == ["c.txt", "d.txt"]
    assert second.json()["has_more"] is True

    third = client.get(
        "/api/v1/files/user-1/project-1",
        params={"limit": 2, "cursor": second.json()["next_cursor"]},
    )
    assert third.status_code == 200
    assert third.json() == {
        "files": ["e.txt"],
        "has_more": False,
        "next_cursor": None,
    }


def test_cursor_remains_usable_when_previous_page_last_file_is_deleted(client):
    for filename in ("a.txt", "b.txt", "c.txt", "d.txt"):
        assert upload(client, filename, filename.encode()).status_code == 201

    first = client.get("/api/v1/files/user-1/project-1?limit=2")
    cursor = first.json()["next_cursor"]
    assert client.delete("/api/v1/files/user-1/project-1/b.txt").status_code == 204

    second = client.get(
        "/api/v1/files/user-1/project-1",
        params={"limit": 2, "cursor": cursor},
    )
    assert second.status_code == 200
    assert second.json() == {
        "files": ["c.txt", "d.txt"],
        "has_more": False,
        "next_cursor": None,
    }


def test_metadata_listing_paginates_before_calculating_checksums(client, monkeypatch):
    from vsem_fms.app.core.async_fs import AsyncFileManager

    for filename in ("a.txt", "b.txt", "c.txt", "d.txt"):
        assert upload(client, filename, filename.encode()).status_code == 201

    original = AsyncFileManager._calculate_sha256
    hashed_files: list[str] = []

    async def counting_sha256(self, file_path):
        hashed_files.append(file_path.name)
        return await original(self, file_path)

    monkeypatch.setattr(AsyncFileManager, "_calculate_sha256", counting_sha256)

    first = client.get("/api/v1/files/user-1/project-1/metadata?limit=2")
    assert first.status_code == 200
    assert [item["filename"] for item in first.json()["files"]] == ["a.txt", "b.txt"]
    assert first.json()["has_more"] is True
    assert len(hashed_files) == 2

    second = client.get(
        "/api/v1/files/user-1/project-1/metadata",
        params={"limit": 2, "cursor": first.json()["next_cursor"]},
    )
    assert second.status_code == 200
    assert [item["filename"] for item in second.json()["files"]] == ["c.txt", "d.txt"]
    assert second.json()["has_more"] is False
    assert second.json()["next_cursor"] is None
    assert len(hashed_files) == 4


def test_pagination_rejects_invalid_cursor_and_out_of_range_limit(client):
    assert upload(client, "a.txt", b"a").status_code == 201

    response = client.get(
        "/api/v1/files/user-1/project-1",
        params={"limit": 2, "cursor": "not-a-valid-cursor"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid pagination cursor."

    assert client.get("/api/v1/files/user-1/project-1?limit=0").status_code == 422
    assert client.get("/api/v1/files/user-1/project-1?limit=501").status_code == 422


def _registry_key(
    secret: str,
    *,
    key_id: str,
    scopes: set[str],
    folder_prefix: str | None = None,
    enabled: bool = True,
):
    from vsem_fms.app.core.api_keys import APIKeyConfig
    from vsem_fms.app.core.api_keys import hash_api_key

    return APIKeyConfig(
        id=key_id,
        name=f"Test {key_id}",
        secret_hash=hash_api_key(secret),
        enabled=enabled,
        scopes=scopes,
        folder_prefix=folder_prefix,
    )


def test_read_only_registry_key_can_read_but_cannot_write_or_delete(client, monkeypatch):
    secret = "fms_live_readonly_0123456789"

    # Seed a file using the backward-compatible legacy admin key.
    assert upload(client, "readonly.txt", b"payload").status_code == 201

    monkeypatch.setattr(settings, "API_KEY", None)
    monkeypatch.setattr(
        settings,
        "API_KEYS",
        [_registry_key(secret, key_id="reader", scopes={"files:read", "files:list"})],
    )
    client.headers.update({"X-API-Key": secret})

    response = client.get("/api/v1/files/user-1/project-1")
    assert response.status_code == 200

    response = client.get("/api/v1/files/user-1/project-1/readonly.txt")
    assert response.status_code == 200

    response = upload(client, "blocked.txt", b"nope")
    assert response.status_code == 403

    response = client.delete("/api/v1/files/user-1/project-1/readonly.txt")
    assert response.status_code == 403


def test_folder_scoped_key_cannot_escape_its_logical_folder(client, monkeypatch):
    secret = "fms_live_folder_scope_0123456789"
    assert upload(client, "allowed.txt", b"allowed").status_code == 201

    monkeypatch.setattr(settings, "API_KEY", None)
    monkeypatch.setattr(
        settings,
        "API_KEYS",
        [
            _registry_key(
                secret,
                key_id="project-reader",
                scopes={"files:read", "files:list"},
                folder_prefix="user-1/project-1",
            )
        ],
    )
    client.headers.update({"X-API-Key": secret})

    assert client.get("/api/v1/files/user-1/project-1").status_code == 200
    assert client.get("/api/v1/files/user-1/project-1/allowed.txt").status_code == 200

    response = client.get("/api/v1/files/user-1/project-2")
    assert response.status_code == 403

    response = client.get("/api/v1/files/user-2/project-1")
    assert response.status_code == 403


def test_disabled_registry_key_is_unauthorized(client, monkeypatch):
    secret = "fms_live_disabled_0123456789"
    monkeypatch.setattr(settings, "API_KEY", None)
    monkeypatch.setattr(
        settings,
        "API_KEYS",
        [_registry_key(secret, key_id="disabled", scopes={"files:list"}, enabled=False)],
    )
    client.headers.update({"X-API-Key": secret})

    response = client.get("/api/v1/files/user-1/project-1")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "ApiKey"


def test_admin_registry_key_bypasses_operation_scopes(client, monkeypatch):
    secret = "fms_live_admin_0123456789"
    monkeypatch.setattr(settings, "API_KEY", None)
    monkeypatch.setattr(
        settings,
        "API_KEYS",
        [_registry_key(secret, key_id="admin", scopes={"admin"})],
    )
    client.headers.update({"X-API-Key": secret})

    assert upload(client, "admin.txt", b"payload").status_code == 201
    assert client.get("/api/v1/files/user-1/project-1/admin.txt").status_code == 200
    assert client.delete("/api/v1/files/user-1/project-1/admin.txt").status_code == 204


def test_api_client_identity_is_added_to_request_completion_log(client, monkeypatch):
    import json

    from loguru import logger

    secret = "fms_live_audit_0123456789"
    monkeypatch.setattr(settings, "API_KEY", None)
    monkeypatch.setattr(
        settings,
        "API_KEYS",
        [_registry_key(secret, key_id="audit-client", scopes={"files:list"})],
    )
    client.headers.update({"X-API-Key": secret})

    captured: list[str] = []
    sink_id = logger.add(captured.append, serialize=True)
    try:
        response = client.get("/api/v1/files/user-1/project-1")
    finally:
        logger.remove(sink_id)

    # The folder may not exist in this isolated test; authentication/audit still completed.
    assert response.status_code in {200, 404}
    events = [json.loads(item)["record"] for item in captured]
    completion = next(event for event in events if event["message"] == "HTTP request completed")
    assert completion["extra"]["api_client_id"] == "audit-client"
    assert completion["extra"]["api_client_name"] == "Test audit-client"
