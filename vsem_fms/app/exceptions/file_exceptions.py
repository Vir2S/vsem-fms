class FileOperationError(Exception):
    """Base class for all file operation errors."""

    def __init__(self, detail: str = "An error occurred during file operation"):
        self.detail = detail
        super().__init__(detail)


class FileUploadError(FileOperationError):
    def __init__(self, detail: str = "Failed to upload file"):
        super().__init__(detail)


class FileAlreadyExistsError(FileOperationError):
    def __init__(self, file_name: str):
        super().__init__(f"File '{file_name}' already exists.")


class FileSizeError(FileOperationError):
    def __init__(self, size: int | None, limit: int):
        size_label = "unknown" if size is None else f"{round(size / 1024 / 1024, 2)}MB"
        limit_label = f"{round(limit / 1024 / 1024, 2)}MB"
        super().__init__(f"File size {size_label} exceeds the allowed limit of {limit_label}.")
        self.size = size
        self.limit = limit


class InvalidFileNameError(FileOperationError):
    def __init__(self, file_name: str | None):
        super().__init__(f"Invalid file name: {file_name!r}.")


class FileWriteError(FileOperationError):
    def __init__(self, path: str):
        super().__init__(f"Failed to write file: {path}")


class FileNotFound(FileOperationError):
    def __init__(self, folder: str, subfolder: str, file_name: str):
        super().__init__(f"File not found: {file_name} in {folder}/{subfolder}")


class FolderNotFoundError(FileOperationError):
    def __init__(self, folder: str, subfolder: str):
        super().__init__(f"Folder '{folder}/{subfolder}' not found.")


class FileReadError(FileOperationError):
    def __init__(self, path: str):
        super().__init__(f"Failed to read file: {path}")


class InvalidFileEncodingError(FileOperationError):
    def __init__(self, detail: str = "Invalid file encoding."):
        super().__init__(detail)


class UnsupportedFileTypeError(FileOperationError):
    def __init__(self, detail: str = "Unsupported file type."):
        super().__init__(detail)


class InsufficientStorageError(FileOperationError):
    def __init__(self, free_bytes: int, required_free_bytes: int):
        super().__init__(
            "Insufficient storage space: "
            f"{round(free_bytes / 1024 / 1024, 2)}MB free, "
            f"at least {round(required_free_bytes / 1024 / 1024, 2)}MB must remain."
        )
        self.free_bytes = free_bytes
        self.required_free_bytes = required_free_bytes
