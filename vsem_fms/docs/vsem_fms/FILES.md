# Files API

Base path: `/api/v1`

All file endpoints require the `X-API-Key` header. VSEM FMS supports the backward-compatible single `API_KEY` as well as a hashed `API_KEYS` registry with per-client scopes and optional logical-folder restrictions.

Operation scopes:

- upload: `files:write`
- retrieve file, metadata, or `HEAD`: `files:read`
- list filenames or metadata: `files:list`
- delete: `files:delete`
- `admin`: all operations

Missing, unknown, or disabled keys return `401`; an authenticated key outside its scope or folder restriction returns `403`.

## Upload a file

`POST /api/v1/files`

Multipart form fields:

- `file`: required file upload
- `folder`: required logical parent folder
- `subfolder`: required logical subfolder
- `overwrite`: optional boolean, defaults to `true`

Example:

```bash
curl -X POST http://localhost:5000/api/v1/files \
  -H "X-API-Key: replace-with-a-long-random-secret" \
  -F "folder=project_data" \
  -F "subfolder=2026_analytics" \
  -F "overwrite=true" \
  -F "file=@report.pdf"
```

Success: `201 Created`

```json
{
  "message": "File uploaded successfully.",
  "path": "project_data/2026_analytics/report.pdf"
}
```

Errors:

- `400 Bad Request`: invalid filename or file exceeds `MAX_FILE_SIZE_MB`
- `409 Conflict`: file exists and `overwrite=false`
- `422 Unprocessable Entity`: missing or invalid form fields
- `500 Internal Server Error`: storage write failure

Uploads use temp files plus an atomic commit. If validation fails while overwriting an existing file, the existing file remains untouched.

## List files

`GET /api/v1/files/{folder}/{subfolder}`

Success: `200 OK`

```json
{
  "files": [
    "file1.txt",
    "report.pdf"
  ]
}
```

Only logical filenames are returned; absolute storage paths are never exposed.

### Cursor pagination

Add `limit` (1-500) to opt into cursor pagination. A paginated response adds `has_more` and `next_cursor`; use that cursor on the next request. If `cursor` is supplied without `limit`, the default page size is 100. Requests without either query parameter keep the legacy `{"files": [...]}` response unchanged.

```http
GET /api/v1/files/{folder}/{subfolder}?limit=100&cursor={next_cursor}
```

```json
{
  "files": ["file1.txt", "report.pdf"],
  "has_more": true,
  "next_cursor": "opaque-token"
}
```

The metadata listing endpoint supports the same `limit` and `cursor` parameters. It calculates SHA-256 only for files on the requested page.

## List file metadata

`GET /api/v1/files/{folder}/{subfolder}/metadata`

Returns metadata for every listable file while leaving the original filename-only list endpoint unchanged. Each item contains:

- `filename`
- `size` in bytes
- `content_type`
- `modified_at` as UTC ISO 8601
- `sha256`

## Retrieve file metadata

`GET /api/v1/files/{folder}/{subfolder}/{filename}/metadata`

Returns the same metadata for one logical file. SHA-256 is calculated in chunks so the file is not loaded fully into memory.

## Retrieve file headers

`HEAD /api/v1/files/{folder}/{subfolder}/{filename}`

Returns no body and includes `Content-Length`, `Content-Type`, `Last-Modified`, `ETag`, and `X-Checksum-SHA256`.

## Retrieve a file

`GET /api/v1/files/{folder}/{subfolder}/{filename}`

For UTF-8 `.txt`, `.csv`, `.md`, `.json`, and `.xml` files the response is JSON:

```json
{
  "filename": "file1.txt",
  "content": "This is the file content."
}
```

All other file types are streamed directly from disk. Unknown extensions fall back to `application/octet-stream` when a MIME type cannot be inferred.

Errors:

- `400 Bad Request`: invalid filename or invalid UTF-8 for an inline text file
- `404 Not Found`: file or folder not found

## Delete a file

`DELETE /api/v1/files/{folder}/{subfolder}/{filename}`

Success: `204 No Content`

Deletion accepts the original logical filename. It also supports files written by v1.0.0 using the previous hashed-filename storage scheme.

Errors:

- `400 Bad Request`: invalid filename
- `404 Not Found`: file or folder not found
