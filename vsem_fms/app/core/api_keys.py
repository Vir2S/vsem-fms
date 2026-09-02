from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import re

from pydantic import BaseModel, Field, field_validator


_API_KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


class APIScope(StrEnum):
    """Permissions that can be granted to an API key."""

    FILES_READ = "files:read"
    FILES_WRITE = "files:write"
    FILES_DELETE = "files:delete"
    FILES_LIST = "files:list"
    ADMIN = "admin"


class APIKeyConfig(BaseModel):
    """Hashed API-key record loaded from application settings."""

    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    secret_hash: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    enabled: bool = True
    scopes: set[APIScope] = Field(min_length=1)
    folder_prefix: str | None = Field(default=None, max_length=512)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        value = value.strip()
        if not value or not _API_KEY_ID_PATTERN.fullmatch(value):
            raise ValueError("API key id may contain only letters, numbers, '.', '_' and '-'")
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("API key name must not be blank")
        return value

    @field_validator("secret_hash")
    @classmethod
    def normalize_secret_hash(cls, value: str) -> str:
        return value.lower()

    @field_validator("folder_prefix")
    @classmethod
    def validate_folder_prefix(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip().strip("/")
        if not value or value == "*":
            return None
        if "\\" in value or "\x00" in value:
            raise ValueError("folder_prefix contains an invalid path separator")

        parts = value.split("/")
        if parts[-1] == "*":
            parts = parts[:-1]
        if not parts or len(parts) > 2:
            raise ValueError("folder_prefix must be a folder or folder/subfolder path")
        if any(not part or part in {".", ".."} for part in parts):
            raise ValueError("folder_prefix contains a reserved path segment")

        return "/".join(parts)


def hash_api_key(secret: str) -> str:
    """Return the SHA-256 digest used by the multi-key registry."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class APIPrincipal:
    """Authenticated API client identity used for authorization and audit logs."""

    id: str
    name: str
    scopes: frozenset[APIScope]
    folder_prefix: str | None = None
    legacy: bool = False

    def has_scope(self, scope: APIScope) -> bool:
        return APIScope.ADMIN in self.scopes or scope in self.scopes
