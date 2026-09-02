from vsem_fms.app.storage.base import StorageBackend
from vsem_fms.app.storage.local import LocalStorageBackend


def get_storage_backend() -> StorageBackend:
    """Build the configured storage backend for one dependency scope."""
    return LocalStorageBackend()
