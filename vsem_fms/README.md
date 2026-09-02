# VSEM FMS

VSEM FMS is an asynchronous file management service built with FastAPI and AnyIO. It provides API-key protected upload, listing, retrieval, and deletion of files while keeping logical folder identifiers separate from the internal storage layout.

## Requirements

- Python 3.11+
- pip
- Docker is optional

## Local setup

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Configure authentication in `.env` before starting the service. Existing deployments can keep using the legacy `API_KEY`; new deployments should prefer the hashed `API_KEYS` registry described below. The application refuses to start if neither mechanism is configured.

```env
API_KEY=replace-with-a-long-random-secret
API_KEYS=[]
STORAGE_PATH=./storage
MAX_FILE_SIZE_MB=100
MIN_FREE_DISK_SPACE_MB=1024
MAX_FILE_AGE_HOURS=168
CLEANUP_INTERVAL_SECONDS=3600
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_DIR=./logs
SERVER_HOST=0.0.0.0
SERVER_PORT=5000
```

`MAX_FILE_SIZE` is still accepted as a backward-compatible alias for `MAX_FILE_SIZE_MB` when upgrading from v1.0.0.

Start the application:

```bash
python -m vsem_fms.app.main
```

Alternatively:

```bash
uvicorn vsem_fms.app.main:app --host 0.0.0.0 --port 5000
```

OpenAPI documentation is available at `http://localhost:5000/api/v1/docs`.

## Request tracing and structured logs

Every HTTP response includes an `X-Request-ID` header. If the client sends its own `X-Request-ID` (up to 128 characters), VSEM FMS preserves it; otherwise the server generates a UUID. The same ID is attached to logs emitted while handling that request.

`LOG_FORMAT=json` (default) writes structured JSON logs to stdout and `app.log`. Set `LOG_FORMAT=text` for human-readable local logs. Request completion events include the HTTP method, path, status code, duration in milliseconds, client IP, request ID, and authenticated API client identity when available.

## API authentication

Protected endpoints require the `X-API-Key` header. The `/api/v1/ping` health endpoint remains public.

The legacy `API_KEY` setting is still supported and is treated as an unrestricted admin credential so existing deployments continue to work. For multiple clients, use `API_KEYS`, which stores only SHA-256 hashes and supports per-key permissions, revocation, and logical-folder restrictions. Both mechanisms may coexist during a rotation or migration.

Generate a new high-entropy credential and its server-side hash:

```bash
python -m vsem_fms.commands.hash_api_key --generate
```

The command prints the client secret once and its SHA-256 hash. Give the `secret` to the client and store only the `sha256` value in the server registry:

```env
API_KEYS='[{"id":"crm-prod","name":"CRM production","secret_hash":"<64-char-sha256>","enabled":true,"scopes":["files:read","files:write","files:list"],"folder_prefix":"crm/*"}]'
```

Available scopes are:

- `files:read` — download files, read JSON content, metadata, and `HEAD` headers
- `files:write` — upload or overwrite files
- `files:delete` — delete files
- `files:list` — list filenames and metadata
- `admin` — grants every operation scope

`folder_prefix` is optional. A value such as `crm` or `crm/*` grants access to every subfolder under the logical `crm` folder; `crm/contracts` grants access only to that exact folder/subfolder pair. Omit it for unrestricted folder access. A valid key without the required scope or folder permission receives `403 Forbidden`; missing, unknown, or disabled credentials receive `401 Unauthorized`.

Disable one credential with `"enabled": false` without affecting any other client. Request completion logs include `api_client_id` and `api_client_name`, making authenticated activity attributable to a specific integration.

```bash
curl -H "X-API-Key: <client-secret>" \
  http://localhost:5000/api/v1/files/crm/contracts
```

## File API

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/api/v1/files` | Upload a file using multipart form data |
| `GET` | `/api/v1/files/{folder}/{subfolder}` | List logical filenames |
| `GET` | `/api/v1/files/{folder}/{subfolder}/metadata` | List file metadata |
| `GET` | `/api/v1/files/{folder}/{subfolder}/{filename}` | Retrieve a file |
| `HEAD` | `/api/v1/files/{folder}/{subfolder}/{filename}` | Retrieve file metadata as headers |
| `GET` | `/api/v1/files/{folder}/{subfolder}/{filename}/metadata` | Retrieve file metadata as JSON |
| `DELETE` | `/api/v1/files/{folder}/{subfolder}/{filename}` | Delete a file |

### Upload

```bash
curl -X POST http://localhost:5000/api/v1/files \
  -H "X-API-Key: replace-with-a-long-random-secret" \
  -F "folder=user-1" \
  -F "subfolder=project-1" \
  -F "overwrite=true" \
  -F "file=@example.txt"
```

Example response:

```json
{
  "message": "File uploaded successfully.",
  "path": "user-1/project-1/example.txt"
}
```

The response contains a logical path only. Internal filesystem paths are never returned by the API.

### Retrieval behavior

UTF-8 files with `.txt`, `.csv`, `.md`, `.json`, or `.xml` extensions are returned as JSON containing `filename` and `content`. All other extensions are streamed from disk as downloads. Unknown extensions use `application/octet-stream` when no MIME type can be inferred.

Metadata responses expose `filename`, `size`, `content_type`, `modified_at` (UTC), and a streaming-computed `sha256`. `HEAD` returns the same essential metadata through standard headers plus `ETag` and `X-Checksum-SHA256`, without a response body. The original filename-only list endpoint is unchanged for backward compatibility.

### Cursor pagination

Filename and metadata listings support opt-in cursor pagination with `limit` and `cursor` query parameters. Existing requests without either parameter keep the legacy response shape unchanged.

```bash
curl -H "X-API-Key: replace-with-a-long-random-secret" \
  "http://localhost:5000/api/v1/files/user-1/project-1?limit=100"
```

A paginated response includes `has_more` and `next_cursor`:

```json
{
  "files": ["a.txt", "b.txt"],
  "has_more": true,
  "next_cursor": "djEAYi50eHQ"
}
```

Pass `next_cursor` back as the next request's `cursor`. Cursors are opaque and remain usable if the last file from the previous page is deleted between requests. `limit` accepts values from 1 to 500; when only `cursor` is supplied, the page size defaults to 100.

Metadata pagination uses the same parameters and calculates SHA-256 only for files included in the returned page.

### Storage backend architecture

The API/service layer depends on a `StorageBackend` contract rather than directly on the local filesystem implementation. `LocalStorageBackend` is the default backend and preserves the existing on-disk format and legacy v1.0.0 compatibility. The download contract supports both local paths and asynchronous byte streams, so a future S3-compatible backend can be added without changing the public HTTP API.

### Storage behavior

Folder and subfolder identifiers are hashed internally. Starting with v1.0.1, filenames are stored using their validated original names so listing can return meaningful logical filenames. Read and delete operations remain compatible with hashed filenames created by v1.0.0.

Uploads are first written to a temporary file and committed atomically only after size validation succeeds. A failed overwrite therefore does not destroy the previous valid file.

## Docker Compose

Create the runtime environment file and configure either a legacy key or the scoped key registry:

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

For the legacy mode, put the generated value into `API_KEY`. For scoped multi-key mode, use the generator and `API_KEYS` registry above. Then start the service from the repository root:

```bash
docker compose up -d --build
```

Check status and logs:

```bash
docker compose ps
docker compose logs -f vsem-fms
```

Persistent files and logs are bind-mounted to `./storage` and `./logs`. A dedicated cleanup service periodically removes files older than `MAX_FILE_AGE_HOURS`, while uploads preserve at least `MIN_FREE_DISK_SPACE_MB` of free disk space. The image health check uses `/api/v1/ping`, and the service restarts automatically unless it is explicitly stopped.

Stop the service:

```bash
docker compose down
```

## Docker

Build from the repository root:

```bash
docker build -f vsem_fms/Dockerfile -t vsem-fms .
```

Run:

```bash
docker run --rm -p 5000:5000 \
  -e API_KEY='replace-with-a-long-random-secret' \
  -e SERVER_HOST=0.0.0.0 \
  -e SERVER_PORT=5000 \
  -v "$(pwd)/storage:/app/storage" \
  vsem-fms
```

The production entrypoint does not enable Uvicorn reload mode.

## Tests

Install development dependencies and run the suite:

```bash
pip install -r requirements-dev.txt
pytest -q
```

The test suite covers the complete upload/list/get/delete flow, failed overwrite data preservation, `overwrite=false`, arbitrary binary downloads, legacy hashed-file compatibility, scoped multi-key authentication, folder restrictions, disabled-key rejection, audit identity, old-file cleanup, route-safe folder validation, and legacy configuration compatibility.

## Author

Born2CodeLab / Vitaly Sem
