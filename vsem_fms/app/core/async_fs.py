"""Backward-compatible import shim for the local storage backend."""

import shutil

from vsem_fms.app.storage.local import LocalStorageBackend


AsyncFileManager = LocalStorageBackend

__all__ = ["AsyncFileManager", "LocalStorageBackend", "shutil"]
