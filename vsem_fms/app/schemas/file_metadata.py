from pydantic import BaseModel


class FileMetadata(BaseModel):
    """Public metadata exposed for a stored file."""

    filename: str
    size: int
    content_type: str
    modified_at: str
    sha256: str


class FileMetadataList(BaseModel):
    """Metadata listing for files in a logical folder."""

    files: list[FileMetadata]
