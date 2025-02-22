# **VSem Async File System**

### 🚀 Description  
This project is an **asynchronous file system** based on **FastAPI** and **Trio**, with **API Key authentication**.

## 📦 Installation  
```bash
pip install -r requirements.txt
```

## 🚀 Running the Server  
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 🔐 Using the API Key  
All requests must include the `X-API-Key` header:  
```bash
curl -X GET "http://localhost:8000/files/" -H "X-API-Key: my-ultra-secure-key"
```

## 🔥 Key Features:  
- 📂 **Asynchronous file operations** using `trio`  
- 🔑 **API Key authentication**  
- 📜 **Logging** via `loguru`  
- 🛡 **Middleware** for request logging  

## 📄 API Endpoints:  
| Method  | URL                 | Description         |
|---------|---------------------|---------------------|
| `POST`  | `/upload/`          | Upload a file      |
| `GET`   | `/files/`           | List all files     |
| `GET`   | `/files/{filename}` | Download a file    |
| `DELETE`| `/files/{filename}` | Delete a file      |

🔧 **Author**: **Vitaly Sem** 🚀