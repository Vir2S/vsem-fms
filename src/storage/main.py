from fastapi import Depends, FastAPI, File, HTTPException, UploadFile

from logging_setup import setup_logging
from src.async_fs import AsyncFileManager
from src.auth import get_api_key
from src.middleware import trailing_slash_handler_middleware

setup_logging()
app = FastAPI()
# app.middleware("http")(trailing_slash_handler_middleware)
file_manager = AsyncFileManager()

@app.post("/upload/")
async def upload_file(
    file: UploadFile = File(...), api_key: str = Depends(get_api_key)
):
    content = await file.read()
    file_path = await file_manager.write_file(file.filename, content)
    return {"message": "✅ Файл збережено", "path": file_path}

@app.get("/files/")
async def list_files(api_key: str = Depends(get_api_key)):
    files = await file_manager.list_files()
    return {"files": files}

@app.get("/files/{filename}")
async def get_file(filename: str, api_key: str = Depends(get_api_key)):
    try:
        content = await file_manager.read_file(filename)
        return {"filename": filename, "content": content.decode()}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="❌ Файл не знайдено")

@app.delete("/files/{filename}")
async def delete_file(filename: str, api_key: str = Depends(get_api_key)):
    success = await file_manager.delete_file(filename)
    if not success:
        raise HTTPException(status_code=404, detail="❌ Файл не знайдено")
    return {"message": "🗑️ Файл видалено"}
