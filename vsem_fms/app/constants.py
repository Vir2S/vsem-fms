ROOT_API = "/api/v1"
DOCS_URL = f"{ROOT_API}/docs"
REDOC_URL = f"{ROOT_API}/redoc"
OPENAPI_URL = f"{ROOT_API}/openapi.json"


TEXT_EXTENSIONS = {".txt", ".csv", ".md", ".json", ".xml"}
BINARY_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".zip", ".png", ".jpg", ".jpeg", ".gif"}

MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".zip": "application/zip",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
}
