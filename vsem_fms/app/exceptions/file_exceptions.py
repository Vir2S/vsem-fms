class FileOperationError(Exception):
    """Base class for file-operation errors."""

    def __init__(self, detail: str = "An error occurred during file operation"):
        self.detail = detail
        super().__init__(self.detail)


class FileUploadError(FileOperationError):
    """Raised when a file upload operation fails."""

    def __init__(self, detail: str = "Failed to upload file"):
        super().__init__(detail)


class FileAlreadyExistsError(FileOperationError):
    """Raised when overwrite is disabled and the file already exists."""

    def __init__(self, file_name: str):
        super().__init__(f"File '{file_name}' already exists.")


class FileSizeError(FileOperationError):
    """Raised when an uploaded file exceeds the configured size limit."""

    def __init__(self, size: int, limit: int):
        detail = (
            f"File size {round(size / 1024 / 1024, 2)}MB "
            f"exceeds the allowed limit of {round(limit / 1024 / 1024, 2)}MB."
        )
        super().__init__(detail)


class InvalidFileNameError(FileOperationError):
    """Raised when an uploaded or requested filename is unsafe or empty."""

    def __init__(self, detail: str = "Invalid file name."):
        super().__init__(detail)


class FileWriteError(FileOperationError):
    """Raised when a file cannot be written to storage."""

    def __init__(self, path: str):
        super().__init__(f"Failed to write file to path: {path}")


class FileNotFound(FileOperationError):
    """Raised when the requested file does not exist."""

    def __init__(self, folder: str, subfolder: str, file_name: str):
        super().__init__(f"File not found: {file_name} in {folder}/{subfolder}")


class FolderNotFoundError(FileOperationError):
    """Raised when the requested logical directory does not exist."""

    def __init__(self, folder: str, subfolder: str):
        super().__init__(f"Folder '{folder}/{subfolder}' not found.")


class FileReadError(FileOperationError):
    """Raised when a file cannot be read from storage."""

    def __init__(self, path: str):
        super().__init__(f"Failed to read file from path: {path}")


class InvalidFileEncodingError(FileOperationError):
    """Raised when text content is not valid UTF-8."""

    def __init__(self, detail: str = "Invalid file encoding."):
        super().__init__(detail)


class UnsupportedFileTypeError(FileOperationError):
    """Raised when a file extension is not supported by the response layer."""

    def __init__(self, detail: str = "Unsupported file type."):
        super().__init__(detail)
