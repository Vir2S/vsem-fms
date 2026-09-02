# Changelog

## [Unreleased]

### Added

- Added file metadata endpoints with `size`, `content_type`, `modified_at`, and streaming SHA-256 checksums, plus `HEAD` support with metadata headers and ETags.
- Added cursor-based pagination for filename and metadata listings with `limit`, opaque cursors, `has_more`, and `next_cursor`, while preserving the legacy unpaginated response shape when pagination parameters are omitted.
- Added request correlation through `X-Request-ID`, structured JSON/text logging, request duration/status/response-size fields, and propagation of request context into internal service logs.
- Added scoped multi-key API authentication with hashed key registries, per-key enable/disable state, `files:read`, `files:write`, `files:delete`, `files:list`, and `admin` scopes, optional folder-prefix restrictions, and client identity in request logs.
- Added an API-key generation/hash CLI for provisioning multi-key credentials without requiring the application settings to start first.
- Added an S3-compatible storage backend for AWS S3, Hetzner Object Storage, MinIO, Cloudflare R2, and other standard S3 endpoints, with streaming downloads, multipart uploads, S3-native cursor listing, SHA-256 metadata tags/fallback hashing, and retention cleanup.

### Changed

- Refactored storage access behind a pluggable `StorageBackend` contract and moved local filesystem behavior into `LocalStorageBackend`, keeping the existing HTTP API unchanged.
- Added backend-neutral download handling so remote/object-storage backends can stream data without requiring route or service-layer rewrites.
- Preserved the existing single `API_KEY` as a backward-compatible legacy admin credential while allowing deployments to opt into the new scoped `API_KEYS` registry.

### Fixed

- Restored CI compatibility by pinning AnyIO tests to the asyncio backend, preserving the legacy hashed-filename helper, and returning the domain-specific `InvalidFileNameError` for invalid local filenames.
- Made invalid multipart path validation return HTTP `422` without depending on Starlette status-constant naming, and aligned the legacy authentication test with the `401 Unauthorized` contract for invalid API keys.

### Security

- Invalid or disabled API keys now return HTTP `401 Unauthorized`; authenticated keys that lack the required scope or folder access return HTTP `403 Forbidden`.
- New multi-key credentials are configured and matched by SHA-256 hash rather than storing their plaintext secrets in the key registry.

## [1.0.3] - 2026-09-02

### Added

- Added a dedicated Docker Compose cleanup worker that continuously enforces `MAX_FILE_AGE_HOURS` using the configurable `CLEANUP_INTERVAL_SECONDS` interval.
- Added `MIN_FREE_DISK_SPACE_MB` protection so uploads stop with HTTP `507 Insufficient Storage` before exhausting the storage volume.
- Added GitHub Actions CI for pytest, Python compilation, Docker Compose validation, and Docker image builds on pushes and pull requests.
- Added regression coverage for cleanup deletion counts and disk-exhaustion overwrite safety.

### Changed

- Cleanup cycles now report how many files were deleted.
- Version bumped to `1.0.3`.

## [1.0.2] - 2026-08-28

### Added

- Added root-level `docker-compose.yml` for one-command build and startup with `.env` loading, persistent storage/log bind mounts, automatic restart policy, init handling, and graceful shutdown.
- Added a root `.dockerignore` to keep secrets, runtime data, caches, local environments, and other unnecessary files out of the Docker build context.
- Ignored Docker Compose runtime `storage/` and `logs/` directories from Git.
- Added Docker Compose setup, status, logs, and shutdown instructions to the README.

### Changed

- Version bumped to `1.0.2`.

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
