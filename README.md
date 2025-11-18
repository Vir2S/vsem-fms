# **VSem Async File System**

### 🚀 Description  
This project is an **asynchronous file system** built with **FastAPI** and **Anyio**, secured with **API Key authentication**.

---

## 📂 Getting Started

First, navigate to this service's directory:

```bash
cd vsem_fms
```

## 📦 Installation
```bash
pip install -r requirements.txt
```
## ⚙️ Environment Setup
Copy the example environment file:
```bash
cp .env.example .env
```
Update the `.env` file with your API key and other configurations:
```
API_KEY=your-api-key
STORAGE_PATH=./storage
LOG_LEVEL=INFO
MAX_FILE_SIZE=10
LOG_DIR=logs

SERVER_HOST=localhost
SERVER_PORT=5000

```
---

## 🚀 Running the Server

Run the server locally:

```bash
python app/main.py
```
---
## 🐳 Docker

**> Note**: Docker setup is now described in the [project root README](../README.md).  
If you want to run the entire system with Docker Compose, please refer to that file.

---

---

## 🔐 Using the API Key

All requests must include the `X-API-Key` header. Example:

```bash
curl -X GET "http://localhost:5000/files/" -H "X-API-Key: your-api-key"
```

---

## 🔥 Key Features

- 📂 **Async file operations** via `anyio`
- 🔑 **API Key authentication**
- 📜 **Structured logging** via `loguru`
- 🛡 **Middleware** for request logging

---

## 📄 API Endpoints

| Method   | Endpoint                                | Description     |
|----------|-----------------------------------------|-----------------|
| `POST`   | `/upload`                               | Upload a file   |
| `GET`    | `/files/{folder}/{subfolder}`           | List all files  |
| `GET`    | `/files/{folder}/{subfolder}/{filename}` | Download a file |
| `DELETE` | `/files/{filename}/{folder}/{subfolder}/{filename}`| Delete a file   |

---

🔧 **Author**: **Vitaly Sem** 🚀