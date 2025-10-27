from fastapi import Form
from pydantic import BaseModel, Field


class UploadRequest(BaseModel):
    """
    Request model for uploading a file.
    """

    folder: str = Field(description="The folder where the file will be uploaded.")
    subfolder: str = Field(description="The subfolder where the file will be uploaded.")
    overwrite: bool = Field(default=True, description="Whether to overwrite the file if it already exists.")

    @classmethod
    def as_form(
        cls,
        *,
        folder: str = Form(...),
        subfolder: str = Form(...),
        overwrite: bool = Form(default=True),
    ) -> "UploadRequest":
        return cls(
            folder=folder,
            subfolder=subfolder,
            overwrite=overwrite,
        )


class UploadResponse(BaseModel):
    """
    Response model returned after a successful file upload.
    """

    message: str | None = Field(default=None, description="Confirmation message indicating the upload status.")
    path: str = Field(description="Path to the uploaded model.")
