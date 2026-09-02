from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    API_KEY: str = Field(min_length=16)
    STORAGE_PATH: str = "./storage"
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "./logs"
    MIN_FREE_DISK_SPACE_MB: int = Field(default=1024, ge=0)
    MAX_FILE_SIZE_MB: int = Field(
        default=100,
        gt=0,
        validation_alias=AliasChoices("MAX_FILE_SIZE_MB", "MAX_FILE_SIZE"),
    )
    MAX_FILE_AGE_HOURS: int = Field(default=168, gt=0)
    CLEANUP_INTERVAL_SECONDS: int = Field(default=3600, gt=0)
    SERVER_PORT: int = Field(default=5000, ge=1, le=65535)
    SERVER_HOST: str = "0.0.0.0"

    TITLE: str = "VSEM FMS"
    DESCRIPTION: str = (
        "This server handles File Management System for arbitrary files. "
        "It allows upload, retrieval, listing, and deletion via HTTP REST API."
    )
    VERSION: str = "1.0.3"

    CONTACT: dict[str, str] = {
        "name": "Born2CodeLab",
        "url": "https://born2codelab.com",
        "email": "born2codelab@gmail.com",
    }
    LICENCE_INFO: dict[str, str] = {
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    }


settings = Settings()
