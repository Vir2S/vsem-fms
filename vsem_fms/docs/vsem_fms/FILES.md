# Files API

Base API prefix: `/api/v1`.

All file endpoints require the `X-API-Key` header.

## Upload a file

`POST /api/v1/files`

Content type: `multipart/form-data`.

Fields:

- `folder` — required logical folder name.
- `subfolder` — required logical subfolder name.
- `overwrite` — optional boolean, defaults to `true`.
- `file` — required uploaded file.

Example:

```bash
curl -X POST "http://localhost:5000/api/v1/files" \
  -H "X-API-Key: change-me" \
  -F "folder=project_data" \
  -F "subfolder=2026_analytics" \
  -F "overwrite=true" \
  -F "file=@summary_report.txt"
```

Successful response (`201 Created`):

```json
{
  "message": "File uploaded successfully.",
  "path": "project_data/2026_analytics/summary_report.txt"
}
```

Possible errors:

- `400 Bad Request` — invalid filename or file exceeds the configured size limit.
- `403 Forbidden` — missing or invalid API key.
- `409 Conflict` — file exists and `overwrite=false`.
- `422 Unprocessable Entity` — invalid form data.
- `500 Internal Server Error` — storage write failure.

## List files

`GET /api/v1/files/{folder}/{subfolder}`

Successful response (`200 OK`):

```json
{
  "files": [
    "summary_report.txt",
    "invoice.pdf"
  ]
}
```

The endpoint returns filenames only and does not expose physical hashed storage paths.

## Retrieve a file

`GET /api/v1/files/{folder}/{subfolder}/{filename}`

Text formats (`.txt`, `.csv`, `.md`, `.json`, `.xml`) are returned as JSON:

```json
{
  "filename": "summary_report.txt",
  "content": "..."
}
```

Supported binary formats are returned as attachments.

Possible errors:

- `400 Bad Request` — invalid UTF-8 content for a supported text file.
- `403 Forbidden` — missing or invalid API key.
- `404 Not Found` — folder or file not found.
- `415 Unsupported Media Type` — unsupported extension.

## Delete a file

`DELETE /api/v1/files/{folder}/{subfolder}/{filename}`

Successful response: `204 No Content`.

Possible errors:

- `403 Forbidden` — missing or invalid API key.
- `404 Not Found` — folder or file not found.

## Legacy v1.0.0 files

Version 1.0.0 stored filenames as SHA-256 hashes. v1.0.1 keeps backward-compatible lookup, so existing files remain retrievable/deletable by supplying their original filename. A successful overwrite migrates the file to the current filename format.
