import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """
    Configuration settings for the application.

    Environment variables are loaded using dotenv, allowing easy
    customization without modifying the source code.
    """

    API_KEY: str = os.getenv("API_KEY", "my-ultra-secure-key")
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "./storage")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", 100))  # 100MB max
    SERVER_PORT: str = os.getenv("SERVER_PORT", "5000")
    SERVER_HOST: str = os.getenv("SERVER_HOST", "localhost")

    TITLE: str = "VSEM FMS"

    DESCRIPTION: str = (
        "This server handles File Management System "
        "for any files. It allows upload, retrieve and delete "
        "files via HTTP API."
    )

    VERSION: str = "1.0.0"

    CONTACT: dict[str, str] = {
        "name": "VSEM FMS",
        "url": "https://wattfox.de",
        "email": "born2codelab@gmail.com",
    }

    LICENCE_INFO: dict[str, str] = {"name": "MIT License", "url": "https://opensource.org/licenses/MIT"}


# Initialize the settings object
settings = Settings()
