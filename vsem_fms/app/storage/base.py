from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator

from fastapi import UploadFile


@dataclass(frozen=True, slots=True)
class StorageDownload:
    """Backend-neutral description of a downloadable stored object."""

    filename: str
    content_type: str
    size: int | None = None
    local_path: str | None = None
    stream: AsyncIterator[bytes] | None = None


class StorageBackend(ABC):
    """Storage contract consumed by the application service layer."""

    @abstractmethod
    async def save_file(
        self,
        file: UploadFile,
        folder: str,
        subfolder: str,
        *,
        overwrite: bool = True,
    ) -> None:
        """Persist one logical file."""

    @abstractmethod
    async def read_file(self, folder: str, subfolder: str, filename: str) -> bytes:
        """Read one logical file into memory for inline text responses."""

    @abstractmethod
    async def get_download(self, folder: str, subfolder: str, filename: str) -> StorageDownload:
        """Return a backend-neutral binary download descriptor."""

    @abstractmethod
    async def delete_file(self, folder: str, subfolder: str, filename: str) -> bool:
        """Delete one logical file."""

    @abstractmethod
    async def list_files(self, folder: str, subfolder: str) -> list[str]:
        """List logical filenames."""

    @abstractmethod
    async def list_files_page(
        self,
        folder: str,
        subfolder: str,
        *,
        limit: int,
        after: str | None,
    ) -> tuple[list[str], bool]:
        """List one deterministic cursor page of logical filenames."""

    @abstractmethod
    async def get_file_metadata(self, folder: str, subfolder: str, filename: str) -> dict[str, object]:
        """Return public metadata for one logical file."""

    @abstractmethod
    async def list_file_metadata(self, folder: str, subfolder: str) -> list[dict[str, object]]:
        """Return public metadata for all listable files."""

    @abstractmethod
    async def list_file_metadata_page(
        self,
        folder: str,
        subfolder: str,
        *,
        limit: int,
        after: str | None,
    ) -> tuple[list[dict[str, object]], bool]:
        """Return one deterministic cursor page of file metadata."""

    @abstractmethod
    async def cleanup_old_files(self) -> int:
        """Delete expired files and return the number removed."""
