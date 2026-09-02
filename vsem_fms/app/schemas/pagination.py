from pydantic import BaseModel

from vsem_fms.app.schemas.file_metadata import FileMetadataList


class FileNameList(BaseModel):
    """Backward-compatible filename-only listing."""

    files: list[str]


class FileNamePage(FileNameList):
    """Cursor-paginated filename listing."""

    has_more: bool
    next_cursor: str | None


class FileMetadataPage(FileMetadataList):
    """Cursor-paginated metadata listing."""

    has_more: bool
    next_cursor: str | None
