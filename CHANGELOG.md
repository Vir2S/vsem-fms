# Changelog

## [1.0.1] - 2026-08-27

### Fixed

- Prevented data loss when an oversized or otherwise failed upload attempts to overwrite an existing file by using temporary files and atomic commits.
- Fixed DELETE so callers can delete files using the same original filename used for upload and retrieval.
- Preserved read/delete compatibility with files stored under the legacy v1.0.0 hashed-filename format.
- Stopped file-list and upload responses from exposing internal absolute filesystem paths.
- Made arbitrary/unknown binary file types downloadable instead of returning `415 Unsupported Media Type`.
- Replaced fake in-memory binary streaming with `FileResponse` disk streaming.
- Removed the hard-coded fallback API key and switched API-key comparison to `secrets.compare_digest`.
- Unified environment names around `MAX_FILE_SIZE_MB`, retained backward compatibility with legacy `MAX_FILE_SIZE`, added `MAX_FILE_AGE_HOURS` and `LOG_DIR`, and removed hard-coded file-size error limits.
- Fixed old-file cleanup by adding the missing `MAX_FILE_AGE_HOURS` setting.
- Fixed concurrent directory creation with `exist_ok=True` and reduced upload race conditions with atomic file commit semantics.
- Fixed Docker startup to use `SERVER_PORT`, corrected the Python import path, removed production `--reload`, and made storage/log path initialization safe.
- Fixed logging so `LOG_LEVEL` and `LOG_DIR` are actually respected.
- Rejected reserved (`.` / `..`) and whitespace-only logical folder segments so uploaded files always remain addressable through the REST API.
- Restored Docker `EXPOSE 5000` and an HTTP health check against `/api/v1/ping`.
- Added FastAPI contact metadata and corrected the Born2CodeLab URL.
- Corrected local run commands, API endpoint documentation, multipart upload documentation, and configuration examples.

### Changed

- New uploads keep validated original filenames inside the already-hashed folder/subfolder hierarchy so list responses can return meaningful filenames without a separate metadata database.
- Version bumped to `1.0.1`.

### Added

- Integration and regression tests for upload/list/get/delete, overwrite safety, conflict handling, arbitrary binary downloads, legacy storage/configuration compatibility, authentication, cleanup, and route-safe folder validation.
- `requirements-dev.txt` for the test dependencies.
- `pytest.ini` so the documented `pytest -q` command reliably imports the local package.
