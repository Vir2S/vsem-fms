from fastapi import Form
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ValidationError, field_validator


class UploadRequest(BaseModel):
    """Request model for uploading a file."""

    folder: str = Field(description="The logical folder where the file will be uploaded.")
    subfolder: str = Field(description="The logical subfolder where the file will be uploaded.")
    overwrite: bool = Field(default=True, description="Whether to overwrite the file if it already exists.")

    @field_validator("folder", "subfolder")
    @classmethod
    def validate_path_segment(cls, value: str) -> str:
        """Keep logical path segments compatible with path-parameter endpoints."""
        if (
            not value.strip()
            or value in {".", ".."}
            or "/" in value
            or "\\" in value
            or "\x00" in value
        ):
            raise ValueError("Folder and subfolder must be non-empty path segments.")
        return value

    @classmethod
    def as_form(
        cls,
        *,
        folder: str = Form(...),
        subfolder: str = Form(...),
        overwrite: bool = Form(default=True),
    ) -> "UploadRequest":
        try:
            return cls(folder=folder, subfolder=subfolder, overwrite=overwrite)
        except ValidationError as exc:
            raise RequestValidationError(exc.errors()) from exc


class UploadResponse(BaseModel):
    """Response model returned after a successful file upload."""

    message: str | None = Field(default=None, description="Confirmation message indicating the upload status.")
    path: str = Field(description="Logical path to the uploaded file.")
