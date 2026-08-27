# Changelog

All notable changes to VSEM FMS are documented here. Entries are ordered newest first.

## [1.0.1] - 2026-08-27

### Fixed

- Fixed DELETE using an unhashed filename while v1.0.0 stored hashed filenames, which caused valid files to return `404` on deletion.
- Fixed file listing returning physical hashed paths that were incompatible with subsequent GET/DELETE calls.
- Preserved backward-compatible access to files stored with the v1.0.0 hashed-filename format.
- Fixed failed oversized overwrites deleting the previously valid file by switching uploads to temporary-file + atomic replace semantics.
- Fixed upload-size configuration mismatch (`MAX_FILE_SIZE` vs `MAX_FILE_SIZE_MB`) while retaining the old environment variable as a compatibility alias.
- Added the missing `MAX_FILE_AGE_HOURS` setting used by cleanup logic.
- Fixed Docker startup using undefined `EXPOSE_PORT`; the container now uses `SERVER_PORT` and starts the correct `vsem_fms.app.main:app` module.
- Fixed Docker `PYTHONPATH`, runtime user creation, storage/log directory initialization, and removed development `--reload` from container startup.
- Added a container health check against `/api/v1/ping`.
- Fixed logging so `LOG_LEVEL` and `LOG_DIR` are actually respected.
- Fixed the Born2CodeLab contact URL and added application contact metadata to OpenAPI.
- Fixed stale README/API documentation, incorrect endpoints, incorrect local run command, and the obsolete `custom_file_name` field.
- Hardened API-key comparison using `secrets.compare_digest`.
- Added filename validation to reject path-like or empty filenames.
- Added upload validation for invalid logical folder/subfolder path segments.

### Changed

- Public filenames are preserved on disk inside hashed logical folder/subfolder directories, keeping the external API consistent while still obscuring namespace directories.
- Upload responses now return the logical API path instead of leaking the physical hashed storage path.
- Application version bumped to `1.0.1`.

### Tests

- Added end-to-end API coverage for upload → list → get → delete.
- Added legacy hashed-file compatibility coverage.
- Added regression coverage for atomic oversized overwrite handling and unsafe filenames.
