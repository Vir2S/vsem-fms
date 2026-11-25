import hashlib
import io
from datetime import datetime, timedelta, timezone
from email.message import Message
from typing import Any

import pytest
from botocore.exceptions import ClientError
from fastapi import UploadFile

from vsem_fms.app.config import settings
from vsem_fms.app.exceptions.file_exceptions import FileSizeError, FolderNotFoundError
from vsem_fms.app.storage.s3 import S3StorageBackend


def _not_found(operation: str) -> ClientError:
    return ClientError({"Error": {"Code": "404", "Message": "Not found"}}, operation)


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[str, dict[str, Any]] = {}
        self.multipart: dict[str, dict[str, Any]] = {}
        self.aborted_uploads: list[str] = []
        self.list_calls: list[dict[str, Any]] = []
        self._next_upload = 1

    @staticmethod
    def _tags_from_query(value: str | None) -> dict[str, str]:
        if not value:
            return {}
        pairs = [item.split("=", 1) for item in value.split("&") if "=" in item]
        return {key: val for key, val in pairs}

    def put_object(self, *, Bucket, Key, Body, ContentType, Tagging=None, IfNoneMatch=None, Metadata=None):
        if IfNoneMatch == "*" and Key in self.objects:
            raise ClientError({"Error": {"Code": "PreconditionFailed"}}, "PutObject")
        self.objects[Key] = {
            "body": bytes(Body),
            "content_type": ContentType,
            "last_modified": datetime.now(timezone.utc),
            "tags": self._tags_from_query(Tagging),
            "metadata": dict(Metadata or {}),
        }
        return {"ETag": '"put-etag"'}

    def head_object(self, *, Bucket, Key):
        if Key not in self.objects:
            raise _not_found("HeadObject")
        item = self.objects[Key]
        return {
            "ContentLength": len(item["body"]),
            "ContentType": item["content_type"],
            "LastModified": item["last_modified"],
            "Metadata": dict(item.get("metadata", {})),
        }

    def get_object(self, *, Bucket, Key):
        if Key not in self.objects:
            raise _not_found("GetObject")
        item = self.objects[Key]
        return {
            "Body": io.BytesIO(item["body"]),
            "ContentLength": len(item["body"]),
            "ContentType": item["content_type"],
            "LastModified": item["last_modified"],
            "Metadata": dict(item.get("metadata", {})),
        }

    def delete_object(self, *, Bucket, Key):
        self.objects.pop(Key, None)
        return {}

    def put_object_tagging(self, *, Bucket, Key, Tagging):
        if Key not in self.objects:
            raise _not_found("PutObjectTagging")
        self.objects[Key]["tags"] = {
            str(item["Key"]): str(item["Value"])
            for item in Tagging.get("TagSet", [])
        }
        return {}

    def get_object_tagging(self, *, Bucket, Key):
        if Key not in self.objects:
            raise _not_found("GetObjectTagging")
        return {
            "TagSet": [
                {"Key": key, "Value": value}
                for key, value in self.objects[Key]["tags"].items()
            ]
        }

    def create_multipart_upload(self, *, Bucket, Key, ContentType, Metadata=None):
        upload_id = f"upload-{self._next_upload}"
        self._next_upload += 1
        self.multipart[upload_id] = {
            "key": Key,
            "content_type": ContentType,
            "metadata": dict(Metadata or {}),
            "parts": {},
        }
        return {"UploadId": upload_id}

    def upload_part(self, *, Bucket, Key, UploadId, PartNumber, Body):
        upload = self.multipart[UploadId]
        upload["parts"][PartNumber] = bytes(Body)
        return {"ETag": f'"part-{PartNumber}"'}

    def complete_multipart_upload(self, *, Bucket, Key, UploadId, MultipartUpload, IfNoneMatch=None):
        if IfNoneMatch == "*" and Key in self.objects:
            raise ClientError({"Error": {"Code": "PreconditionFailed"}}, "CompleteMultipartUpload")
        upload = self.multipart.pop(UploadId)
        body = b"".join(upload["parts"][part["PartNumber"]] for part in MultipartUpload["Parts"])
        self.objects[Key] = {
            "body": body,
            "content_type": upload["content_type"],
            "metadata": upload["metadata"],
            "last_modified": datetime.now(timezone.utc),
            "tags": {},
        }
        return {"ETag": '"multipart-etag"'}

    def abort_multipart_upload(self, *, Bucket, Key, UploadId):
        self.multipart.pop(UploadId, None)
        self.aborted_uploads.append(UploadId)
        return {}

    def list_objects_v2(self, **kwargs):
        self.list_calls.append(dict(kwargs))
        prefix = kwargs.get("Prefix", "")
        keys = sorted(key for key in self.objects if key.startswith(prefix))
        start_after = kwargs.get("StartAfter")
        if start_after:
            keys = [key for key in keys if key > start_after]

        continuation = kwargs.get("ContinuationToken")
        offset = int(continuation) if continuation else 0
        max_keys = int(kwargs.get("MaxKeys", 1000))
        page = keys[offset : offset + max_keys]
        next_offset = offset + len(page)
        truncated = next_offset < len(keys)
        response = {
            "Contents": [
                {
                    "Key": key,
                    "Size": len(self.objects[key]["body"]),
                    "LastModified": self.objects[key]["last_modified"],
                }
                for key in page
            ],
            "IsTruncated": truncated,
        }
        if truncated:
            response["NextContinuationToken"] = str(next_offset)
        return response

    def delete_objects(self, *, Bucket, Delete):
        for item in Delete["Objects"]:
            self.objects.pop(item["Key"], None)
        return {"Errors": []}


class RaceOnPutS3Client(FakeS3Client):
    """Simulate an object appearing after the initial existence check."""

    def __init__(self) -> None:
        super().__init__()
        self.inject_on_put = True

    def put_object(self, *, Bucket, Key, Body, ContentType, Tagging=None, IfNoneMatch=None, Metadata=None):
        if self.inject_on_put and IfNoneMatch == "*":
            self.inject_on_put = False
            self.objects[Key] = {
                "body": b"concurrent",
                "content_type": ContentType,
                "last_modified": datetime.now(timezone.utc),
                "tags": {},
            }
        return super().put_object(
            Bucket=Bucket,
            Key=Key,
            Body=Body,
            ContentType=ContentType,
            Tagging=Tagging,
            IfNoneMatch=IfNoneMatch,
            Metadata=Metadata,
        )


def _upload_file(filename: str, content: bytes, content_type: str = "application/octet-stream") -> UploadFile:
    headers = Message()
    headers["content-type"] = content_type
    return UploadFile(file=io.BytesIO(content), filename=filename, headers=headers)


@pytest.fixture
def s3_backend(monkeypatch):
    monkeypatch.setattr(settings, "S3_BUCKET", "test-bucket")
    monkeypatch.setattr(settings, "S3_PREFIX", "vsem-fms")
    monkeypatch.setattr(settings, "S3_MULTIPART_THRESHOLD_MB", 5)
    monkeypatch.setattr(settings, "S3_MULTIPART_CHUNK_SIZE_MB", 5)
    monkeypatch.setattr(settings, "S3_DOWNLOAD_CHUNK_SIZE_KB", 64)
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_MB", 100)
    client = FakeS3Client()
    return S3StorageBackend(client=client), client


@pytest.mark.anyio
async def test_s3_small_file_round_trip_and_metadata(s3_backend):
    backend, client = s3_backend
    content = b"hello from s3"

    await backend.save_file(
        _upload_file("hello.txt", content, "text/plain"),
        "tenant-a",
        "project-a",
    )

    assert await backend.read_file("tenant-a", "project-a", "hello.txt") == content
    assert await backend.list_files("tenant-a", "project-a") == ["hello.txt"]

    metadata = await backend.get_file_metadata("tenant-a", "project-a", "hello.txt")
    assert metadata["filename"] == "hello.txt"
    assert metadata["size"] == len(content)
    assert metadata["content_type"] == "text/plain"
    assert metadata["sha256"] == hashlib.sha256(content).hexdigest()
    assert metadata["modified_at"].endswith("Z")

    key = next(iter(client.objects))
    assert "tenant-a" not in key
    assert "project-a" not in key
    assert key.endswith("/hello.txt")

    assert await backend.delete_file("tenant-a", "project-a", "hello.txt") is True
    with pytest.raises(FileNotFoundError):
        await backend.read_file("tenant-a", "project-a", "hello.txt")


@pytest.mark.anyio
async def test_s3_binary_download_streams_in_chunks(s3_backend):
    backend, _ = s3_backend
    content = b"x" * (256 * 1024)
    await backend.save_file(_upload_file("blob.bin", content), "tenant", "project")

    download = await backend.get_download("tenant", "project", "blob.bin")

    assert download.local_path is None
    assert download.size == len(content)
    assert download.stream is not None
    chunks = [chunk async for chunk in download.stream]
    assert b"".join(chunks) == content
    assert len(chunks) > 1


@pytest.mark.anyio
async def test_s3_large_upload_uses_multipart_and_preserves_sha256(s3_backend):
    backend, client = s3_backend
    content = b"m" * (6 * 1024 * 1024)

    await backend.save_file(_upload_file("large.bin", content), "tenant", "project")

    assert client.multipart == {}
    metadata = await backend.get_file_metadata("tenant", "project", "large.bin")
    assert metadata["size"] == len(content)
    assert metadata["sha256"] == hashlib.sha256(content).hexdigest()


@pytest.mark.anyio
async def test_s3_oversized_multipart_upload_is_rejected_before_initiation(s3_backend, monkeypatch):
    backend, client = s3_backend
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_MB", 6)
    content = b"z" * (7 * 1024 * 1024)

    with pytest.raises(FileSizeError):
        await backend.save_file(_upload_file("too-large.bin", content), "tenant", "project")

    assert client.aborted_uploads == []
    assert client.multipart == {}
    assert client._next_upload == 1
    assert client.objects == {}


@pytest.mark.anyio
async def test_s3_listing_uses_start_after_for_cursor_pagination(s3_backend):
    backend, client = s3_backend
    for filename in ("a.txt", "b.txt", "c.txt"):
        await backend.save_file(_upload_file(filename, filename.encode()), "tenant", "project")

    first, has_more = await backend.list_files_page("tenant", "project", limit=2, after=None)
    assert first == ["a.txt", "b.txt"]
    assert has_more is True

    second, has_more = await backend.list_files_page("tenant", "project", limit=2, after="b.txt")
    assert second == ["c.txt"]
    assert has_more is False
    assert any(str(call.get("StartAfter", "")).endswith("/b.txt") for call in client.list_calls)


@pytest.mark.anyio
async def test_s3_missing_logical_folder_returns_folder_not_found(s3_backend):
    backend, _ = s3_backend
    with pytest.raises(FolderNotFoundError):
        await backend.list_files("missing", "folder")


@pytest.mark.anyio
async def test_s3_cleanup_removes_only_expired_objects(s3_backend, monkeypatch):
    backend, client = s3_backend
    monkeypatch.setattr(settings, "MAX_FILE_AGE_HOURS", 24)

    await backend.save_file(_upload_file("old.txt", b"old"), "tenant", "project")
    await backend.save_file(_upload_file("new.txt", b"new"), "tenant", "project")

    old_key = next(key for key in client.objects if key.endswith("/old.txt"))
    new_key = next(key for key in client.objects if key.endswith("/new.txt"))
    client.objects[old_key]["last_modified"] = datetime.now(timezone.utc) - timedelta(hours=25)
    client.objects[new_key]["last_modified"] = datetime.now(timezone.utc) - timedelta(hours=1)

    assert await backend.cleanup_old_files() == 1
    assert old_key not in client.objects
    assert new_key in client.objects


@pytest.mark.anyio
async def test_s3_overwrite_false_is_race_safe_for_small_objects(monkeypatch):
    monkeypatch.setattr(settings, "S3_BUCKET", "test-bucket")
    monkeypatch.setattr(settings, "S3_PREFIX", "vsem-fms")
    monkeypatch.setattr(settings, "S3_MULTIPART_THRESHOLD_MB", 5)
    monkeypatch.setattr(settings, "S3_MULTIPART_CHUNK_SIZE_MB", 5)
    client = RaceOnPutS3Client()
    backend = S3StorageBackend(client=client)

    with pytest.raises(FileExistsError):
        await backend.save_file(
            _upload_file("race.txt", b"new-content"),
            "tenant",
            "project",
            overwrite=False,
        )

    key = next(iter(client.objects))
    assert client.objects[key]["body"] == b"concurrent"


@pytest.mark.anyio
async def test_s3_metadata_falls_back_to_stream_hash_when_metadata_is_missing(s3_backend):
    backend, client = s3_backend
    content = b"external-object-without-tag"
    await backend.save_file(_upload_file("external.bin", content), "tenant", "project")
    key = next(key for key in client.objects if key.endswith("/external.bin"))
    client.objects[key]["metadata"] = {}
    # Old tags may be stale even when they look like valid digests.
    client.objects[key]["tags"] = {"sha256": hashlib.sha256(b"wrong object").hexdigest()}

    metadata = await backend.get_file_metadata("tenant", "project", "external.bin")

    assert metadata["sha256"] == hashlib.sha256(content).hexdigest()


def test_s3_client_builder_passes_provider_configuration(monkeypatch):
    import vsem_fms.app.storage.s3 as s3_module

    captured = {}

    def fake_boto_client(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(settings, "S3_BUCKET", "bucket")
    monkeypatch.setattr(settings, "S3_ENDPOINT_URL", "https://objects.example.test")
    monkeypatch.setattr(settings, "S3_REGION", "region-1")
    monkeypatch.setattr(settings, "S3_ACCESS_KEY", "access")
    monkeypatch.setattr(settings, "S3_SECRET_KEY", "secret")
    monkeypatch.setattr(settings, "S3_SESSION_TOKEN", "token")
    monkeypatch.setattr(settings, "S3_ADDRESSING_STYLE", "path")
    monkeypatch.setattr(settings, "S3_VERIFY_SSL", False)
    monkeypatch.setattr(settings, "S3_MAX_POOL_CONNECTIONS", 48)
    monkeypatch.setattr(s3_module.boto3, "client", fake_boto_client)

    S3StorageBackend()

    assert captured["service_name"] == "s3"
    assert captured["endpoint_url"] == "https://objects.example.test"
    assert captured["region_name"] == "region-1"
    assert captured["aws_access_key_id"] == "access"
    assert captured["aws_secret_access_key"] == "secret"
    assert captured["aws_session_token"] == "token"
    assert captured["verify"] is False
    assert captured["config"].s3["addressing_style"] == "path"
    assert captured["config"].max_pool_connections == 48


def test_s3_backend_round_trip_through_public_http_api(client, s3_backend):
    from vsem_fms.app.main import app
    from vsem_fms.app.storage.dependencies import get_storage_backend

    backend, _ = s3_backend
    app.dependency_overrides[get_storage_backend] = lambda: backend
    try:
        uploaded = client.post(
            "/api/v1/files",
            data={"folder": "tenant", "subfolder": "project", "overwrite": "true"},
            files={"file": ("remote.bin", b"remote-api-content", "application/octet-stream")},
        )
        assert uploaded.status_code == 201

        listing = client.get("/api/v1/files/tenant/project?limit=10")
        assert listing.status_code == 200
        assert listing.json() == {
            "files": ["remote.bin"],
            "has_more": False,
            "next_cursor": None,
        }

        metadata = client.get("/api/v1/files/tenant/project/remote.bin/metadata")
        assert metadata.status_code == 200
        assert metadata.json()["sha256"] == hashlib.sha256(b"remote-api-content").hexdigest()

        downloaded = client.get("/api/v1/files/tenant/project/remote.bin")
        assert downloaded.status_code == 200
        assert downloaded.content == b"remote-api-content"

        deleted = client.delete("/api/v1/files/tenant/project/remote.bin")
        assert deleted.status_code == 204
        assert client.get("/api/v1/files/tenant/project/remote.bin").status_code == 404
    finally:
        app.dependency_overrides.pop(get_storage_backend, None)


def test_s3_pool_reused_across_requests_and_closed_on_shutdown(monkeypatch, api_key):
    from fastapi.testclient import TestClient
    from unittest.mock import Mock

    from vsem_fms.app.main import app

    clients = []

    def build_client():
        sdk = FakeS3Client()
        sdk.close = Mock()
        clients.append(sdk)
        return sdk

    monkeypatch.setattr(settings, "STORAGE_BACKEND", "s3")
    monkeypatch.setattr(settings, "S3_BUCKET", "test-bucket")
    monkeypatch.setattr(S3StorageBackend, "_build_client", staticmethod(build_client))
    headers = {"X-API-Key": api_key}

    for cycle in range(2):
        with TestClient(app) as client:
            backend = app.state.storage_backend
            assert len(clients) == cycle + 1
            assert backend.client is clients[-1]
            response = client.post(
                "/api/v1/files",
                headers=headers,
                data={"folder": "tenant", "subfolder": "project"},
                files={"file": ("shared.bin", b"shared pool")},
            )
            assert response.status_code == 201
            listing = client.get("/api/v1/files/tenant/project", headers=headers)
            assert listing.json() == {"files": ["shared.bin"]}
            downloaded = client.get("/api/v1/files/tenant/project/shared.bin", headers=headers)
            assert downloaded.content == b"shared pool"
            assert app.state.storage_backend is backend
            assert len(clients) == cycle + 1
            clients[-1].close.assert_not_called()
        clients[-1].close.assert_called_once_with()
        assert not hasattr(app.state, "storage_backend")


def test_local_lifespan_does_not_build_s3_client(monkeypatch):
    from unittest.mock import Mock
    from fastapi.testclient import TestClient

    from vsem_fms.app.main import app

    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    builder = Mock(side_effect=AssertionError("Local storage must not initialize S3"))
    monkeypatch.setattr(S3StorageBackend, "_build_client", builder)
    with TestClient(app) as client:
        assert client.get("/api/v1/ping").status_code == 200
    builder.assert_not_called()


@pytest.mark.anyio
async def test_s3_backend_does_not_close_borrowed_client(s3_backend):
    from unittest.mock import Mock

    backend, sdk = s3_backend
    sdk.close = Mock()
    await backend.aclose()
    sdk.close.assert_not_called()


@pytest.mark.anyio
async def test_cleanup_worker_closes_owned_pool_on_cancellation(monkeypatch):
    import asyncio
    from unittest.mock import Mock

    from vsem_fms.commands.cleanup import run_cleanup_loop

    sdk = FakeS3Client()
    sdk.close = Mock()
    builder = Mock(return_value=sdk)
    reached_cleanup = asyncio.Event()

    async def cleanup(self):
        reached_cleanup.set()
        return 0

    monkeypatch.setattr(settings, "STORAGE_BACKEND", "s3")
    monkeypatch.setattr(settings, "S3_BUCKET", "test-bucket")
    monkeypatch.setattr(S3StorageBackend, "_build_client", builder)
    monkeypatch.setattr(S3StorageBackend, "cleanup_old_files", cleanup)
    task = asyncio.create_task(run_cleanup_loop())
    try:
        await asyncio.wait_for(reached_cleanup.wait(), timeout=5)
        sdk.close.assert_not_called()
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    builder.assert_called_once_with()
    sdk.close.assert_called_once_with()


@pytest.mark.anyio
@pytest.mark.parametrize("second_is_multipart", [False, True])
async def test_s3_concurrent_overwrites_publish_matching_checksum(s3_backend, monkeypatch, second_is_multipart):
    import asyncio
    from unittest.mock import Mock

    backend, sdk = s3_backend
    first = b"a" * (6 * 1024 * 1024)
    second = b"b" * (7 * 1024 * 1024) if second_is_multipart else b"new"
    committed = asyncio.Event()
    resume = asyncio.Event()
    original_call = backend._call
    first_complete = True

    async def interleaved_call(method_name, **kwargs):
        nonlocal first_complete
        result = await original_call(method_name, **kwargs)
        if method_name == "complete_multipart_upload" and first_complete:
            first_complete = False
            committed.set()
            await resume.wait()
        return result

    monkeypatch.setattr(backend, "_call", interleaved_call)
    sdk.put_object_tagging = Mock(side_effect=AssertionError("No post-commit tagging"))
    sdk.get_object_tagging = Mock(side_effect=AssertionError("No legacy tag reads"))
    task = asyncio.create_task(backend.save_file(_upload_file("race.bin", first), "tenant", "project"))
    try:
        await asyncio.wait_for(committed.wait(), timeout=5)
        initial = await backend.get_file_metadata("tenant", "project", "race.bin")
        assert initial["sha256"] == hashlib.sha256(first).hexdigest()
        await backend.save_file(_upload_file("race.bin", second), "tenant", "project")
    finally:
        resume.set()
        await asyncio.wait_for(task, timeout=5)
    metadata = await backend.get_file_metadata("tenant", "project", "race.bin")
    assert metadata["size"] == len(second)
    assert metadata["sha256"] == hashlib.sha256(second).hexdigest()
    assert await backend.read_file("tenant", "project", "race.bin") == second
    sdk.put_object_tagging.assert_not_called()
    sdk.get_object_tagging.assert_not_called()


@pytest.mark.anyio
@pytest.mark.parametrize("large", [False, True])
async def test_s3_new_metadata_uses_head_without_downloading(s3_backend, monkeypatch, large):
    from unittest.mock import Mock

    backend, sdk = s3_backend
    content = b"x" * (6 * 1024 * 1024) if large else b"small"
    await backend.save_file(_upload_file("object.bin", content), "tenant", "project")
    monkeypatch.setattr(sdk, "get_object", Mock(side_effect=AssertionError("Unexpected body download")))
    monkeypatch.setattr(sdk, "get_object_tagging", Mock(side_effect=AssertionError("Unexpected tag read")))
    metadata = await backend.get_file_metadata("tenant", "project", "object.bin")
    assert metadata["sha256"] == hashlib.sha256(content).hexdigest()
    assert sdk.objects[next(iter(sdk.objects))]["metadata"]["sha256"] == metadata["sha256"]


@pytest.mark.anyio
async def test_s3_legacy_metadata_uses_single_get_snapshot_on_overwrite(s3_backend, monkeypatch):
    backend, sdk = s3_backend
    await backend.save_file(_upload_file("old.bin", b"old"), "tenant", "project")
    key = next(iter(sdk.objects))
    sdk.objects[key]["metadata"] = {}
    original_head = sdk.head_object
    modified = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    newer = b"new object with different length"

    def racing_head(**kwargs):
        old = original_head(**kwargs)
        sdk.objects[key] = {
            "body": newer,
            "content_type": "application/pdf",
            "last_modified": modified,
            "metadata": {},
            "tags": {"sha256": hashlib.sha256(b"old").hexdigest()},
        }
        return old

    monkeypatch.setattr(sdk, "head_object", racing_head)
    metadata = await backend.get_file_metadata("tenant", "project", "old.bin")
    assert metadata == {
        "filename": "old.bin",
        "size": len(newer),
        "content_type": "application/pdf",
        "modified_at": "2026-01-02T03:04:05Z",
        "sha256": hashlib.sha256(newer).hexdigest(),
    }


@pytest.mark.anyio
async def test_s3_multipart_source_change_aborts_and_preserves_existing_object(s3_backend, monkeypatch):
    backend, sdk = s3_backend
    await backend.save_file(_upload_file("same.bin", b"original"), "tenant", "project")
    upload = _upload_file("same.bin", b"x" * (6 * 1024 * 1024))
    original_seek = upload.seek

    async def mutate_on_rewind(offset):
        upload.file.seek(offset)
        upload.file.write(b"y")
        await original_seek(offset)

    monkeypatch.setattr(upload, "seek", mutate_on_rewind)
    with pytest.raises(OSError, match="Upload content changed"):
        await backend.save_file(upload, "tenant", "project")
    assert sdk.aborted_uploads == ["upload-1"]
    assert sdk.multipart == {}
    assert await backend.read_file("tenant", "project", "same.bin") == b"original"


@pytest.mark.anyio
async def test_s3_multipart_part_failure_aborts_and_preserves_existing_object(s3_backend, monkeypatch):
    backend, sdk = s3_backend
    await backend.save_file(_upload_file("same.bin", b"original"), "tenant", "project")

    def failing_part(**kwargs):
        raise ClientError({"Error": {"Code": "InternalError"}}, "UploadPart")

    monkeypatch.setattr(sdk, "upload_part", failing_part)
    with pytest.raises(OSError, match="S3 multipart upload failed"):
        await backend.save_file(_upload_file("same.bin", b"x" * (6 * 1024 * 1024)), "tenant", "project")
    assert sdk.aborted_uploads == ["upload-1"]
    assert sdk.multipart == {}
    assert await backend.read_file("tenant", "project", "same.bin") == b"original"


@pytest.mark.anyio
async def test_s3_multipart_conditional_commit_preserves_concurrent_writer(s3_backend, monkeypatch):
    backend, sdk = s3_backend
    original_complete = sdk.complete_multipart_upload
    concurrent = b"concurrent writer"

    def racing_complete(**kwargs):
        sdk.put_object(
            Bucket=kwargs["Bucket"], Key=kwargs["Key"], Body=concurrent,
            ContentType="application/octet-stream",
            Metadata={"sha256": hashlib.sha256(concurrent).hexdigest()},
        )
        return original_complete(**kwargs)

    monkeypatch.setattr(sdk, "complete_multipart_upload", racing_complete)
    with pytest.raises(FileExistsError):
        await backend.save_file(
            _upload_file("race.bin", b"x" * (6 * 1024 * 1024)),
            "tenant", "project", overwrite=False,
        )
    assert sdk.multipart == {}
    assert sdk.aborted_uploads == ["upload-1"]
    assert await backend.read_file("tenant", "project", "race.bin") == concurrent
    metadata = await backend.get_file_metadata("tenant", "project", "race.bin")
    assert metadata["sha256"] == hashlib.sha256(concurrent).hexdigest()
