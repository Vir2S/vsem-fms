import hashlib
import mimetypes
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from functools import partial
from typing import Any

import boto3
from anyio import to_thread
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import UploadFile
from loguru import logger

from vsem_fms.app.config import settings
from vsem_fms.app.exceptions.file_exceptions import FileSizeError, FolderNotFoundError
from vsem_fms.app.storage.base import StorageBackend, StorageDownload


_SHA256_TAG = "sha256"
_NOT_FOUND_CODES = {"404", "NoSuchKey", "NotFound"}
_PRECONDITION_FAILED_CODES = {"412", "PreconditionFailed"}


class S3StorageBackend(StorageBackend):
    """S3-compatible storage backend using the synchronous AWS SDK off the event loop."""

    def __init__(self, client: Any | None = None) -> None:
        self.bucket = settings.S3_BUCKET or ""
        self.prefix = settings.S3_PREFIX.strip("/")
        self.multipart_threshold = settings.S3_MULTIPART_THRESHOLD_MB * 1024 * 1024
        self.multipart_chunk_size = settings.S3_MULTIPART_CHUNK_SIZE_MB * 1024 * 1024
        self.download_chunk_size = settings.S3_DOWNLOAD_CHUNK_SIZE_KB * 1024
        self.client = client or self._build_client()

    @staticmethod
    def _build_client() -> Any:
        client_kwargs: dict[str, Any] = {
            "service_name": "s3",
            "config": Config(s3={"addressing_style": settings.S3_ADDRESSING_STYLE}),
            "verify": settings.S3_VERIFY_SSL,
        }
        if settings.S3_ENDPOINT_URL:
            client_kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
        if settings.S3_REGION:
            client_kwargs["region_name"] = settings.S3_REGION
        if settings.S3_ACCESS_KEY:
            client_kwargs["aws_access_key_id"] = settings.S3_ACCESS_KEY
            client_kwargs["aws_secret_access_key"] = settings.S3_SECRET_KEY
        if settings.S3_SESSION_TOKEN:
            client_kwargs["aws_session_token"] = settings.S3_SESSION_TOKEN
        return boto3.client(**client_kwargs)

    async def _call(self, method_name: str, **kwargs: Any) -> Any:
        method = getattr(self.client, method_name)
        return await to_thread.run_sync(partial(method, **kwargs))

    @staticmethod
    def _validate_filename(filename: str | None) -> str:
        if not filename or filename in {".", ".."} or "/" in filename or "\\" in filename or "\x00" in filename:
            raise ValueError("Invalid filename")
        return filename

    @staticmethod
    def _hash_segment(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    def _folder_key_prefix(self, folder: str, subfolder: str) -> str:
        parts = [self._hash_segment(folder), self._hash_segment(subfolder)]
        if self.prefix:
            parts.insert(0, self.prefix)
        return "/".join(parts) + "/"

    def _object_key(self, folder: str, subfolder: str, filename: str) -> str:
        safe_filename = self._validate_filename(filename)
        return f"{self._folder_key_prefix(folder, subfolder)}{safe_filename}"

    def _cleanup_prefix(self) -> str:
        return f"{self.prefix}/" if self.prefix else ""

    @staticmethod
    def _error_code(exc: ClientError) -> str:
        return str(exc.response.get("Error", {}).get("Code", ""))

    @classmethod
    def _is_not_found(cls, exc: ClientError) -> bool:
        return cls._error_code(exc) in _NOT_FOUND_CODES

    @classmethod
    def _is_precondition_failed(cls, exc: ClientError) -> bool:
        return cls._error_code(exc) in _PRECONDITION_FAILED_CODES

    async def _object_exists(self, key: str) -> bool:
        try:
            await self._call("head_object", Bucket=self.bucket, Key=key)
            return True
        except ClientError as exc:
            if self._is_not_found(exc):
                return False
            raise

    async def _get_object(self, key: str) -> dict[str, Any]:
        try:
            return await self._call("get_object", Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if self._is_not_found(exc):
                raise FileNotFoundError(key) from exc
            raise

    async def _close_body(self, body: Any) -> None:
        close = getattr(body, "close", None)
        if close is not None:
            await to_thread.run_sync(close)

    async def _read_body(self, body: Any) -> bytes:
        try:
            return await to_thread.run_sync(body.read)
        finally:
            await self._close_body(body)

    async def _iter_body(self, body: Any) -> AsyncIterator[bytes]:
        try:
            while True:
                chunk = await to_thread.run_sync(body.read, self.download_chunk_size)
                if not chunk:
                    break
                yield chunk
        finally:
            await self._close_body(body)

    async def _set_sha256_tag(self, key: str, digest: str) -> None:
        try:
            await self._call(
                "put_object_tagging",
                Bucket=self.bucket,
                Key=key,
                Tagging={"TagSet": [{"Key": _SHA256_TAG, "Value": digest}]},
            )
        except ClientError:
            # The file is already safely stored. Metadata can still calculate the
            # digest by streaming the object when tagging permissions are absent.
            logger.warning("Could not persist SHA-256 tag for S3 object '{}'", key)

    async def _read_upload_chunk(self, file: UploadFile, size: int, digest: Any, total: int) -> tuple[bytes, int]:
        chunk = await file.read(size)
        if not chunk:
            return b"", total
        total += len(chunk)
        max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if total > max_size:
            raise FileSizeError(size=total, limit=max_size)
        digest.update(chunk)
        return chunk, total

    async def _put_small_object(
        self,
        *,
        key: str,
        body: bytes,
        content_type: str,
        digest: str,
        overwrite: bool,
    ) -> None:
        kwargs: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": key,
            "Body": body,
            "ContentType": content_type,
            "Tagging": f"{_SHA256_TAG}={digest}",
        }
        if not overwrite:
            kwargs["IfNoneMatch"] = "*"
        await self._call("put_object", **kwargs)

    async def _multipart_upload(
        self,
        *,
        file: UploadFile,
        key: str,
        initial_buffer: bytearray,
        content_type: str,
        digest: Any,
        total_size: int,
        overwrite: bool,
    ) -> str:
        created = await self._call(
            "create_multipart_upload",
            Bucket=self.bucket,
            Key=key,
            ContentType=content_type,
        )
        upload_id = created["UploadId"]
        parts: list[dict[str, Any]] = []
        part_number = 1
        buffer = initial_buffer

        try:
            while True:
                while len(buffer) >= self.multipart_chunk_size:
                    payload = bytes(buffer[: self.multipart_chunk_size])
                    del buffer[: self.multipart_chunk_size]
                    uploaded = await self._call(
                        "upload_part",
                        Bucket=self.bucket,
                        Key=key,
                        UploadId=upload_id,
                        PartNumber=part_number,
                        Body=payload,
                    )
                    parts.append({"ETag": uploaded["ETag"], "PartNumber": part_number})
                    part_number += 1

                chunk, total_size = await self._read_upload_chunk(
                    file,
                    self.multipart_chunk_size,
                    digest,
                    total_size,
                )
                if not chunk:
                    break
                buffer.extend(chunk)

            if buffer:
                uploaded = await self._call(
                    "upload_part",
                    Bucket=self.bucket,
                    Key=key,
                    UploadId=upload_id,
                    PartNumber=part_number,
                    Body=bytes(buffer),
                )
                parts.append({"ETag": uploaded["ETag"], "PartNumber": part_number})

            complete_kwargs: dict[str, Any] = {
                "Bucket": self.bucket,
                "Key": key,
                "UploadId": upload_id,
                "MultipartUpload": {"Parts": parts},
            }
            if not overwrite:
                complete_kwargs["IfNoneMatch"] = "*"
            await self._call("complete_multipart_upload", **complete_kwargs)
        except BaseException:
            try:
                await self._call(
                    "abort_multipart_upload",
                    Bucket=self.bucket,
                    Key=key,
                    UploadId=upload_id,
                )
            except Exception:
                logger.exception("Failed to abort S3 multipart upload for '{}'", key)
            raise

        sha256 = digest.hexdigest()
        await self._set_sha256_tag(key, sha256)
        return sha256

    async def save_file(
        self,
        file: UploadFile,
        folder: str,
        subfolder: str,
        *,
        overwrite: bool = True,
    ) -> None:
        filename = self._validate_filename(file.filename)
        key = self._object_key(folder, subfolder, filename)

        if not overwrite and await self._object_exists(key):
            raise FileExistsError(f"File {filename} already exists")

        content_type = file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        digest = hashlib.sha256()
        total_size = 0
        initial = bytearray()

        while len(initial) < self.multipart_threshold:
            chunk, total_size = await self._read_upload_chunk(
                file,
                min(self.multipart_chunk_size, self.multipart_threshold - len(initial)),
                digest,
                total_size,
            )
            if not chunk:
                sha256 = digest.hexdigest()
                try:
                    await self._put_small_object(
                        key=key,
                        body=bytes(initial),
                        content_type=content_type,
                        digest=sha256,
                        overwrite=overwrite,
                    )
                except ClientError as exc:
                    if self._is_precondition_failed(exc):
                        raise FileExistsError(f"File {filename} already exists") from exc
                    raise OSError(f"S3 upload failed for {key}") from exc
                logger.info("File saved successfully: '{}'", filename)
                return
            initial.extend(chunk)

        try:
            await self._multipart_upload(
                file=file,
                key=key,
                initial_buffer=initial,
                content_type=content_type,
                digest=digest,
                total_size=total_size,
                overwrite=overwrite,
            )
        except FileSizeError:
            raise
        except ClientError as exc:
            if self._is_precondition_failed(exc):
                raise FileExistsError(f"File {filename} already exists") from exc
            raise OSError(f"S3 multipart upload failed for {key}") from exc

        logger.info("File saved successfully: '{}'", filename)

    async def read_file(self, folder: str, subfolder: str, filename: str) -> bytes:
        key = self._object_key(folder, subfolder, filename)
        response = await self._get_object(key)
        return await self._read_body(response["Body"])

    async def get_download(self, folder: str, subfolder: str, filename: str) -> StorageDownload:
        key = self._object_key(folder, subfolder, filename)
        response = await self._get_object(key)
        content_type = response.get("ContentType") or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        return StorageDownload(
            filename=filename,
            content_type=content_type,
            size=int(response.get("ContentLength", 0)),
            stream=self._iter_body(response["Body"]),
        )

    async def delete_file(self, folder: str, subfolder: str, filename: str) -> bool:
        key = self._object_key(folder, subfolder, filename)
        if not await self._object_exists(key):
            raise FileNotFoundError(key)
        await self._call("delete_object", Bucket=self.bucket, Key=key)
        logger.info("File deleted: '{}/{}/{}'", folder, subfolder, filename)
        return True

    async def _list_direct_objects(
        self,
        folder: str,
        subfolder: str,
        *,
        target_count: int | None = None,
        after: str | None = None,
    ) -> list[dict[str, Any]]:
        prefix = self._folder_key_prefix(folder, subfolder)
        continuation_token: str | None = None
        direct_objects: list[dict[str, Any]] = []

        while True:
            kwargs: dict[str, Any] = {
                "Bucket": self.bucket,
                "Prefix": prefix,
                "MaxKeys": 1000,
            }
            if continuation_token:
                kwargs["ContinuationToken"] = continuation_token
            elif after is not None:
                kwargs["StartAfter"] = f"{prefix}{after}"

            response = await self._call("list_objects_v2", **kwargs)
            for item in response.get("Contents", []):
                key = str(item["Key"])
                relative = key[len(prefix) :] if key.startswith(prefix) else ""
                if not relative or "/" in relative:
                    continue
                direct_objects.append(item)
                if target_count is not None and len(direct_objects) >= target_count:
                    return direct_objects

            if not response.get("IsTruncated"):
                break
            continuation_token = response.get("NextContinuationToken")
            if not continuation_token:
                break

        return direct_objects

    async def _folder_has_objects(self, folder: str, subfolder: str) -> bool:
        objects = await self._list_direct_objects(folder, subfolder, target_count=1)
        return bool(objects)

    async def list_files(self, folder: str, subfolder: str) -> list[str]:
        prefix = self._folder_key_prefix(folder, subfolder)
        objects = await self._list_direct_objects(folder, subfolder)
        if not objects:
            raise FolderNotFoundError(folder=folder, subfolder=subfolder)
        return [str(item["Key"])[len(prefix) :] for item in objects]

    async def list_files_page(
        self,
        folder: str,
        subfolder: str,
        *,
        limit: int,
        after: str | None,
    ) -> tuple[list[str], bool]:
        prefix = self._folder_key_prefix(folder, subfolder)
        objects = await self._list_direct_objects(folder, subfolder, target_count=limit + 1, after=after)
        if not objects:
            if after is not None and await self._folder_has_objects(folder, subfolder):
                return [], False
            raise FolderNotFoundError(folder=folder, subfolder=subfolder)
        names = [str(item["Key"])[len(prefix) :] for item in objects]
        return names[:limit], len(names) > limit

    async def _get_sha256_tag(self, key: str) -> str | None:
        try:
            response = await self._call("get_object_tagging", Bucket=self.bucket, Key=key)
        except ClientError:
            return None
        for tag in response.get("TagSet", []):
            if tag.get("Key") == _SHA256_TAG:
                value = str(tag.get("Value", ""))
                if len(value) == 64 and all(char in "0123456789abcdef" for char in value.lower()):
                    return value.lower()
        return None

    async def _calculate_sha256(self, key: str) -> str:
        tagged = await self._get_sha256_tag(key)
        if tagged:
            return tagged

        response = await self._get_object(key)
        body = response["Body"]
        digest = hashlib.sha256()
        try:
            while True:
                chunk = await to_thread.run_sync(body.read, self.download_chunk_size)
                if not chunk:
                    break
                digest.update(chunk)
        finally:
            await self._close_body(body)
        return digest.hexdigest()

    @staticmethod
    def _format_modified_at(value: Any) -> str:
        if isinstance(value, datetime):
            modified = value
        else:
            modified = datetime.fromisoformat(str(value))
        if modified.tzinfo is None:
            modified = modified.replace(tzinfo=timezone.utc)
        return modified.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    async def get_file_metadata(self, folder: str, subfolder: str, filename: str) -> dict[str, object]:
        key = self._object_key(folder, subfolder, filename)
        try:
            head = await self._call("head_object", Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if self._is_not_found(exc):
                raise FileNotFoundError(key) from exc
            raise
        return {
            "filename": filename,
            "size": int(head.get("ContentLength", 0)),
            "content_type": head.get("ContentType") or mimetypes.guess_type(filename)[0] or "application/octet-stream",
            "modified_at": self._format_modified_at(head["LastModified"]),
            "sha256": await self._calculate_sha256(key),
        }

    async def list_file_metadata(self, folder: str, subfolder: str) -> list[dict[str, object]]:
        filenames = await self.list_files(folder, subfolder)
        return [await self.get_file_metadata(folder, subfolder, filename) for filename in filenames]

    async def list_file_metadata_page(
        self,
        folder: str,
        subfolder: str,
        *,
        limit: int,
        after: str | None,
    ) -> tuple[list[dict[str, object]], bool]:
        filenames, has_more = await self.list_files_page(folder, subfolder, limit=limit, after=after)
        metadata = [await self.get_file_metadata(folder, subfolder, filename) for filename in filenames]
        return metadata, has_more

    async def cleanup_old_files(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.MAX_FILE_AGE_HOURS)
        prefix = self._cleanup_prefix()
        continuation_token: str | None = None
        keys_to_delete: list[dict[str, str]] = []

        while True:
            kwargs: dict[str, Any] = {"Bucket": self.bucket, "Prefix": prefix, "MaxKeys": 1000}
            if continuation_token:
                kwargs["ContinuationToken"] = continuation_token
            response = await self._call("list_objects_v2", **kwargs)
            for item in response.get("Contents", []):
                modified = item.get("LastModified")
                if isinstance(modified, datetime):
                    if modified.tzinfo is None:
                        modified = modified.replace(tzinfo=timezone.utc)
                    if modified < cutoff:
                        keys_to_delete.append({"Key": str(item["Key"])})

            if not response.get("IsTruncated"):
                break
            continuation_token = response.get("NextContinuationToken")
            if not continuation_token:
                break

        deleted = 0
        for start in range(0, len(keys_to_delete), 1000):
            batch = keys_to_delete[start : start + 1000]
            result = await self._call(
                "delete_objects",
                Bucket=self.bucket,
                Delete={"Objects": batch, "Quiet": True},
            )
            # Quiet mode normally omits Deleted entries, so count requested keys
            # unless S3 explicitly reports per-object errors.
            errors = {item.get("Key") for item in result.get("Errors", [])}
            deleted += sum(1 for item in batch if item["Key"] not in errors)

        return deleted
