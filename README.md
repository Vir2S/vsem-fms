# VSEM FMS

VSEM FMS is a small asynchronous file-management API built with FastAPI and AnyIO. It supports authenticated upload, listing, retrieval, and deletion of files stored under logical `folder/subfolder` namespaces.

## Requirements

- Python 3.11+
- An API key configured through environment variables

## Local setup

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` before running the service. At minimum, replace the example API key.

```dotenv
API_KEY=change-me
STORAGE_PATH=./storage
MAX_FILE_SIZE_MB=100
MAX_FILE_AGE_HOURS=24
LOG_LEVEL=INFO
LOG_DIR=./logs
SERVER_HOST=0.0.0.0
SERVER_PORT=5000
```

Start the API:

```bash
python -m vsem_fms.app.main
```

Swagger UI is available at:

```text
http://localhost:5000/api/v1/docs
```

## Authentication

Protected endpoints require the `X-API-Key` header:

```bash
-H "X-API-Key: change-me"
```

## API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/files` | Upload a file |
| `GET` | `/api/v1/files/{folder}/{subfolder}` | List filenames |
| `GET` | `/api/v1/files/{folder}/{subfolder}/{filename}` | Retrieve a file |
| `DELETE` | `/api/v1/files/{folder}/{subfolder}/{filename}` | Delete a file |
| `GET` | `/api/v1/ping` | Health check |

### Upload example

The upload endpoint accepts `multipart/form-data`.

```bash
curl -X POST "http://localhost:5000/api/v1/files" \
  -H "X-API-Key: change-me" \
  -F "folder=customer-1" \
  -F "subfolder=project-1" \
  -F "overwrite=true" \
  -F "file=@example.txt"
```

Example response:

```json
{
  "message": "File uploaded successfully.",
  "path": "customer-1/project-1/example.txt"
}
```

### List files

```bash
curl "http://localhost:5000/api/v1/files/customer-1/project-1" \
  -H "X-API-Key: change-me"
```

```json
{
  "files": ["example.txt"]
}
```

## Storage behavior

Folder and subfolder names are hashed on disk, so the physical storage layout does not expose those logical identifiers. Starting with v1.0.1, public filenames are preserved inside those hashed directories, which keeps upload/list/get/delete behavior consistent.

Files created by v1.0.0 with hashed filenames remain readable and deletable when the original filename is supplied. Overwriting such a file migrates it to the v1.0.1 filename format.

Uploads are first written to a temporary file and atomically moved into place only after size validation succeeds. A failed oversized overwrite therefore does not destroy the previous valid file.

## Docker

Build from the repository root:

```bash
docker build -f vsem_fms/Dockerfile -t vsem-fms .
```

Run with the environment file:

```bash
docker run --rm \
  -p 5000:5000 \
  --env-file .env \
  -v "$(pwd)/storage:/app/storage" \
  -v "$(pwd)/logs:/app/logs" \
  vsem-fms
```

The container listens on port `5000` by default. `SERVER_PORT` can be changed through the environment.

## Tests

```bash
python -m unittest discover -s tests -v
```

## License

MIT License.

**Author:** Born2CodeLab / Vitaly Sem
