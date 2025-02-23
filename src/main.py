from fastapi import Depends, FastAPI, File, HTTPException, UploadFile

from auth import get_api_key
from core.async_fs import AsyncFileManager
from logging_setup import setup_logging
from middleware import trailing_slash_handler_middleware

# Initialize logging
setup_logging()

# Create FastAPI application instance
app = FastAPI()

# Add middleware to handle trailing slashes
app.middleware("http")(trailing_slash_handler_middleware)

# Initialize asynchronous file manager
file_manager = AsyncFileManager()


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...), api_key: str = Depends(get_api_key)
):
    """
    Uploads a file asynchronously.

    :param file: Uploaded file object.
    :param api_key: API key for authentication.
    :return: JSON response with the saved file path.
    """
    file_path = await file_manager.write_file_stream(file.filename, file)
    return {"message": "✅ File saved successfully", "path": file_path}


@app.get("/files")
async def list_files(api_key: str = Depends(get_api_key)):
    """
    Retrieves a list of stored files.

    :param api_key: API key for authentication.
    :return: JSON response with a list of file paths.
    """
    files = await file_manager.list_files()
    return {"files": files}


@app.get("/files/{filename}")
async def get_file(filename: str, api_key: str = Depends(get_api_key)):
    """
    Retrieves the content of a specific file.

    :param filename: Name of the file to retrieve.
    :param api_key: API key for authentication.
    :return: JSON response with file content.
    :raises HTTPException: If the file is not found.
    """
    try:
        content = await file_manager.read_file(filename)
        return {"filename": filename, "content": content.decode()}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="❌ File not found")


@app.delete("/files/{filename}")
async def delete_file(filename: str, api_key: str = Depends(get_api_key)):
    """
    Deletes a specified file.

    :param filename: Name of the file to delete.
    :param api_key: API key for authentication.
    :return: JSON response confirming file deletion.
    :raises HTTPException: If the file does not exist.
    """
    success = await file_manager.delete_file(filename)
    if not success:
        raise HTTPException(status_code=404, detail="❌ File not found")
    return {"message": "🗑️ File deleted successfully"}
