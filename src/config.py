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
    """API key used for authentication."""

    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "./storage")
    """Path where files are stored on the server."""

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    """Logging level (e.g., DEBUG, INFO, WARNING, ERROR)."""

# Initialize the settings object
settings = Settings()
