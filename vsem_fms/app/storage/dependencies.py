from vsem_fms.app.config import settings
from vsem_fms.app.storage.base import StorageBackend
from vsem_fms.app.storage.local import LocalStorageBackend
from vsem_fms.app.storage.s3 import S3StorageBackend


def get_storage_backend() -> StorageBackend:
    """Build the configured storage backend for one dependency scope."""
    if settings.STORAGE_BACKEND == "s3":
        return S3StorageBackend()
    return LocalStorageBackend()
