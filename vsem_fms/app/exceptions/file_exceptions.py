class FileOperationError(Exception):
    """
    Base class for all exceptions related to file operations.
    """

    def __init__(self, detail: str = "An error occurred during file operation"):
        """
        Initializes the exception with a custom error message.

        Args:
            detail (str): The error message to be displayed.
        """
        self.detail = detail
        super().__init__(self.detail)


class FileUploadError(FileOperationError):
    """
    Exception raised when a file upload operation fails.
    """

    def __init__(self, detail: str = "Failed to upload file"):
        """
        Initializes the exception with a custom error message.

        Args:
            detail (str): The error message to be displayed.
        """
        super().__init__(detail)


class FileAlreadyExistsError(FileOperationError):
    """
    Exception raised when trying to upload a file that already exists.
    """

    def __init__(self, file_name: str):
        """
        Initializes the exception with the name of the existing file.

        Args:
            file_name (str): Name of the file that already exists.
        """
        detail = f"File '{file_name}' already exists."
        super().__init__(detail)


class FileSizeError(FileOperationError):
    """
    Exception raised when the uploaded file size exceeds the allowed limit.
    """

    def __init__(self, size: int, limit: int):
        """
        Initializes the exception with file size and limit.

        Args:
            size (int): The size of the uploaded file.
            limit (int): The maximum allowed file size.
        """
        detail = (
            f"File size {round(size / 1024 / 1024, 2)}MB"
            f" exceeds the allowed limit of {round(limit / 1024 / 1024, 2)}MB."
        )
        super().__init__(detail)


class FileWriteError(FileOperationError):
    """
    Exception raised when an error occurs while writing the file to storage.
    """

    def __init__(self, path: str):
        """
        Initializes the exception with the file path where the error occurred.

        Args:
            path (str): The path where the file could not be written.
        """
        detail = f"Failed to write file to path: {path}"
        super().__init__(detail)


class FileNotFound(FileOperationError):
    """
    Raised when the specified folder or subfolder is not found.
    """

    def __init__(self, folder: str, subfolder: str, file_name: str):
        """
        Initialize the exception with the folder and subfolder names.

        Args:
            folder (str): The parent folder name.
            subfolder (str): The subfolder name.
        """
        detail = f"File not found: {file_name} in {folder}/{subfolder}"
        super().__init__(detail)


class FolderNotFoundError(FileOperationError):
    """
    Raised when the specified directory or subdirectory is not found.
    """

    def __init__(self, folder: str, subfolder: str):
        """
        Initialize the exception with the folder and subfolder names.

        Args:
            folder (str): The parent folder name.
            subfolder (str): The subfolder name.
        """
        detail = f"Folder '{folder}/{subfolder}' not found."
        super().__init__(detail)


class FileReadError(FileOperationError):
    """
    Raised when there is an error reading a file.
    """

    def __init__(self, path: str):
        """
        Initialize the exception with the file path where the error occurred.

        Args:
            path (str): The path where the file could not be read.
        """
        detail = f"Failed to read file from path: {path}"
        super().__init__(detail)


class InvalidFileEncodingError(FileOperationError):
    """
    Raised when the file content is not valid UTF-8 text.
    """

    def __init__(self, detail: str = "Invalid file encoding."):
        """
        Initialize the exception with a default or custom error message.

        Args:
            detail (str): The error message to be displayed.
        """
        super().__init__(detail)


class UnsupportedFileTypeError(FileOperationError):
    """
    Raised when the file type (extension) is not supported.
    """

    def __init__(self, detail: str = "Unsupported file type."):
        """
        Initialize the exception with a default or custom error message.

        Args:
            detail (str): The error message to be displayed.
        """
        super().__init__(detail)
