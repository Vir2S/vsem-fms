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


# Initialize the settings object
settings = Settings()
