from typing import Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from vsem_fms.app.core.api_keys import APIKeyConfig


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # API_KEY is the backward-compatible single-key setting. New deployments can
    # use API_KEYS with hashed, scoped credentials instead.
    API_KEY: str | None = Field(default=None, min_length=16)
    API_KEYS: list[APIKeyConfig] = Field(default_factory=list)

    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    STORAGE_PATH: str = "./storage"
    S3_ENDPOINT_URL: str | None = None
    S3_REGION: str | None = None
    S3_BUCKET: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_SESSION_TOKEN: str | None = None
    S3_PREFIX: str = "vsem-fms"
    S3_ADDRESSING_STYLE: Literal["auto", "path", "virtual"] = "auto"
    S3_VERIFY_SSL: bool = True
    S3_MULTIPART_THRESHOLD_MB: int = Field(default=8, ge=5)
    S3_MULTIPART_CHUNK_SIZE_MB: int = Field(default=8, ge=5)
    S3_DOWNLOAD_CHUNK_SIZE_KB: int = Field(default=1024, ge=64, le=16384)
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "text"] = "json"
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
    VERSION: str = "1.1.0"

    CONTACT: dict[str, str] = {
        "name": "Born2CodeLab",
        "url": "https://born2codelab.com",
        "email": "born2codelab@gmail.com",
    }
    LICENCE_INFO: dict[str, str] = {
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    }

    @field_validator("API_KEY", mode="before")
    @classmethod
    def normalize_legacy_api_key(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator(
        "S3_ENDPOINT_URL",
        "S3_REGION",
        "S3_BUCKET",
        "S3_ACCESS_KEY",
        "S3_SECRET_KEY",
        "S3_SESSION_TOKEN",
        mode="before",
    )
    @classmethod
    def normalize_optional_s3_value(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def validate_api_credentials(self) -> "Settings":
        if self.API_KEY is None and not self.API_KEYS:
            raise ValueError("Configure API_KEY or at least one API_KEYS credential")

        key_ids = [item.id for item in self.API_KEYS]
        if len(key_ids) != len(set(key_ids)):
            raise ValueError("API_KEYS ids must be unique")

        secret_hashes = [item.secret_hash for item in self.API_KEYS]
        if len(secret_hashes) != len(set(secret_hashes)):
            raise ValueError("API_KEYS secret_hash values must be unique")

        if self.STORAGE_BACKEND == "s3":
            if not self.S3_BUCKET:
                raise ValueError("S3_BUCKET is required when STORAGE_BACKEND=s3")
            if bool(self.S3_ACCESS_KEY) != bool(self.S3_SECRET_KEY):
                raise ValueError("S3_ACCESS_KEY and S3_SECRET_KEY must be configured together")
            if self.S3_MULTIPART_THRESHOLD_MB < self.S3_MULTIPART_CHUNK_SIZE_MB:
                raise ValueError("S3_MULTIPART_THRESHOLD_MB must be >= S3_MULTIPART_CHUNK_SIZE_MB")
        return self


settings = Settings()
