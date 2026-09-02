# Files API

Base path: `/api/v1`

All file endpoints require the `X-API-Key` header.

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
