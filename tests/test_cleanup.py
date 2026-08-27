import os
import time
from pathlib import Path

import pytest

from vsem_fms.app.config import settings
from vsem_fms.app.core.async_fs import AsyncFileManager


@pytest.mark.anyio
async def test_cleanup_old_files_uses_configured_age(tmp_path, monkeypatch):
    storage = tmp_path / "storage"
    storage.mkdir()
    old_file = storage / "old.bin"
    old_file.write_bytes(b"old")
    two_hours_ago = time.time() - 2 * 3600
    os.utime(old_file, (two_hours_ago, two_hours_ago))

    monkeypatch.setattr(settings, "STORAGE_PATH", str(storage))
    monkeypatch.setattr(settings, "MAX_FILE_AGE_HOURS", 1)

    manager = AsyncFileManager()
    await manager.cleanup_old_files()

    assert not Path(old_file).exists()
