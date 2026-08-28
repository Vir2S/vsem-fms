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

Set a strong API key in `.env` before starting the service. `API_KEY` has no default and the application intentionally refuses to start when it is missing or too short.

```env
API_KEY=replace-with-a-long-random-secret
STORAGE_PATH=./storage
MAX_FILE_SIZE_MB=100
MAX_FILE_AGE_HOURS=168
LOG_LEVEL=INFO
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

## API authentication

Protected endpoints require the `X-API-Key` header:

```bash
curl -H "X-API-Key: replace-with-a-long-random-secret" \
  http://localhost:5000/api/v1/files/user-1/project-1
```

The `/api/v1/ping` health endpoint is public.

## File API

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/api/v1/files` | Upload a file using multipart form data |
| `GET` | `/api/v1/files/{folder}/{subfolder}` | List logical filenames |
| `GET` | `/api/v1/files/{folder}/{subfolder}/{filename}` | Retrieve a file |
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

### Storage behavior

Folder and subfolder identifiers are hashed internally. Starting with v1.0.1, filenames are stored using their validated original names so listing can return meaningful logical filenames. Read and delete operations remain compatible with hashed filenames created by v1.0.0.

Uploads are first written to a temporary file and committed atomically only after size validation succeeds. A failed overwrite therefore does not destroy the previous valid file.

## Docker Compose

Create the runtime environment file and set a strong API key:

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Put the generated value into `API_KEY` in `.env`, then start the service from the repository root:

```bash
docker compose up -d --build
```

Check status and logs:

```bash
docker compose ps
docker compose logs -f vsem-fms
```

Persistent files and logs are bind-mounted to `./storage` and `./logs`. The image health check uses `/api/v1/ping`, and the service restarts automatically unless it is explicitly stopped.

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

The test suite covers the complete upload/list/get/delete flow, failed overwrite data preservation, `overwrite=false`, arbitrary binary downloads, legacy hashed-file compatibility, API-key rejection, old-file cleanup, route-safe folder validation, and legacy configuration compatibility.

## Author

Born2CodeLab / Vitaly Sem
