# FILES API

### Available Methods:

- ![POST](https://img.shields.io/badge/POST-%23FFFF00) `api/v1/files`
- ![GET](https://img.shields.io/badge/GET-%2390EE90) `api/v1/files/{folder}/{subfolder}`
- ![GET](https://img.shields.io/badge/GET-%2390EE90) `api/v1/files/{folder}/{subfolder}/{filename}`
- ![DELETE](https://img.shields.io/badge/DELETE-%23FF0000) `api/v1/files/{folder}/{subfolder}/{filename}`

### Security:
- All endpoints require API key authentication.

---

## ![POST](https://img.shields.io/badge/POST-%23FFFF00) Upload a File

**URL**: `POST api/v1/files`

### Description:
Upload a file to the server and save it to the specified folder and subfolder.

### Request Schema: `UploadRequest`
```json
{
  "folder": "project_data",
  "subfolder": "2025_analytics",
  "custom_file_name": "summary_report",
  "overwrite": true
}
```

### Request:
- **file**: Form-data file upload
- **upload_request**: JSON body as shown above

### Response Schema: `UploadResponse`
```json
{
  "message": "File uploaded successfully.",
  "path": "project_data/2025_analytics/summary_report.txt"
}
```

### Success:
- **201 Created**: File uploaded successfully.

### Errors:
- **400 Bad Request**: File size exceeded or malformed request.
- **409 Conflict**: File already exists and overwrite is not allowed.
- **422 Validation Error**: Malformed JSON body or missing required fields.
- **500 Internal Server Error**: File write error.

---

## ![GET](https://img.shields.io/badge/GET/{folder}/{subfolder}-%2390EE90) List Files

**URL**: `GET api/v1/files/{folder}/{subfolder}`

### Description:
Retrieve a list of files from the specified folder and subfolder.

### Success:
```json
{
  "files": [
    "file1.txt",
    "file2.csv",
    "report_final.pdf"
  ]
}
```

- **200 OK**: Files listed successfully.

### Errors:
- **401 Unauthorized**
- **403 Forbidden**
- **404 Not Found**: Folder or subfolder not found.

---

## ![GET](https://img.shields.io/badge/GET/{folder}/{subfolder}/{filename}-%2390EE90) Get File Content

**URL**: `GET api/v1/files/{folder}/{subfolder}/{filename}`

### Description:
Retrieve the content of a specific file.

### Success:
```json
{
  "filename": "file1.txt",
  "content": "This is the file content."
}
```

- **200 OK**

### Errors:
- **401 Unauthorized**
- **403 Forbidden**
- **404 Not Found**: File or folder not found.

---

## ![DELETE](https://img.shields.io/badge/DELETE/{folder}/{subfolder}/{filename}-%23FF0000) Delete a File

**URL**: `DELETE api/v1/files/{folder}/{subfolder}/{filename}`

### Description:
Deletes a specified file from the folder/subfolder.

### Success:
- **204 No Content**

### Errors:
- **401 Unauthorized**
- **403 Forbidden**
- **404 Not Found**: File not found.

---

### Models

#### UploadRequest
```json
{
  "folder": "project_data",
  "subfolder": "reports",
  "custom_file_name": "report_v1",
  "overwrite": true
}
```

- `folder` *(str, required)*: The folder to upload the file.
- `subfolder` *(str, required)*: The subfolder inside the folder.
- `custom_file_name` *(str, optional)*: Optional custom name for the file.
- `overwrite` *(bool, default=true)*: Whether to overwrite if file exists.

#### UploadResponse
```json
{
  "message": "File uploaded successfully.",
  "path": "project_data/reports/report_v1.txt"
}
```

- `message` *(str, optional)*: Upload confirmation message.
- `path` *(str, required)*: Path to the uploaded file.