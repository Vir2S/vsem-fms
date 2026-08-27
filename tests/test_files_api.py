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
