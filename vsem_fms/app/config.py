from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    API_KEY: str = "my-ultra-secure-key"
    STORAGE_PATH: str = "./storage"
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "./logs"
    MAX_FILE_SIZE_MB: int = Field(
        default=100,
        validation_alias=AliasChoices("MAX_FILE_SIZE_MB", "MAX_FILE_SIZE"),
    )
    MAX_FILE_AGE_HOURS: int = 24
    SERVER_PORT: int = 5000
    SERVER_HOST: str = "0.0.0.0"

    TITLE: str = "VSEM FMS"
    DESCRIPTION: str = (
        "This server handles File Management System "
        "for any files. It allows upload, retrieve and delete "
        "files via HTTP REST API."
    )
    VERSION: str = "1.0.1"

    CONTACT: dict[str, str] = {
        "name": "Born2CodeLab",
        "url": "https://born2codelab.com",
        "email": "born2codelab@gmail.com",
    }
    LICENSE_INFO: dict[str, str] = {
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    }


settings = Settings()
