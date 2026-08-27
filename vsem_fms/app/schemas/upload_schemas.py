from fastapi import Form, HTTPException, status
from pydantic import BaseModel, Field, field_validator


_PATH_SEGMENT_PATTERN = r"^[^/\\\x00]+$"
_RESERVED_PATH_SEGMENTS = {".", ".."}


def _validate_routeable_path_segment(value: str) -> str:
    """Reject logical folder names that cannot round-trip through API routes."""
    normalized = value.strip()
    if not normalized or normalized in _RESERVED_PATH_SEGMENTS:
        raise ValueError("Path segment must not be empty, '.', or '..'.")
    return value


class UploadRequest(BaseModel):
    """Form fields used when uploading a file."""

    folder: str = Field(
        min_length=1,
        pattern=_PATH_SEGMENT_PATTERN,
        description="Logical parent folder.",
    )
    subfolder: str = Field(
        min_length=1,
        pattern=_PATH_SEGMENT_PATTERN,
        description="Logical subfolder.",
    )
    overwrite: bool = Field(default=True, description="Replace an existing file with the same name.")

    @field_validator("folder", "subfolder")
    @classmethod
    def validate_routeable_path_segment(cls, value: str) -> str:
        return _validate_routeable_path_segment(value)

    @classmethod
    def as_form(
        cls,
        *,
        folder: str = Form(..., min_length=1, pattern=_PATH_SEGMENT_PATTERN),
        subfolder: str = Form(..., min_length=1, pattern=_PATH_SEGMENT_PATTERN),
        overwrite: bool = Form(default=True),
    ) -> "UploadRequest":
        # FastAPI validates Form constraints before entering this dependency. The
        # checks below cover reserved/whitespace-only segments while keeping an
        # invalid multipart request as an HTTP 422 instead of leaking a raw
        # Pydantic ValidationError from inside the dependency.
        try:
            folder = _validate_routeable_path_segment(folder)
            subfolder = _validate_routeable_path_segment(subfolder)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from exc

        return cls(folder=folder, subfolder=subfolder, overwrite=overwrite)


class UploadResponse(BaseModel):
    """Response returned after a successful upload."""

    message: str = Field(description="Upload confirmation message.")
    path: str = Field(description="Logical file path. Internal filesystem paths are never exposed.")
