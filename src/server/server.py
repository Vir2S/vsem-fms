import uvicorn

from fastapi import FastAPI

from config import settings
from core.logging import logger
from middlewares.slash_trailing import trailing_slash_handler_middleware
from routes import upload, get_file, get_files_list, delete


class Server:
    """
    Class for managing the FastAPI server.

    Provides methods to initialize and run the server with pre-configured routes.
    """

    def __init__(self):
        """
        Initializes the Server instance.

        Creates a FastAPI application instance and attaches necessary routes.
        """
        self.server = self.__create_server()

    def __create_server(self) -> "Server":
        """
        Configures the FastAPI server with the necessary routes.

        This method attaches predefined routers to the server instance.

        Returns:
            FastAPI: Configured FastAPI server.
        """
        # Initialize FastAPI with metadata
        server = FastAPI(
            title=str(settings.TITLE),
            description=str(settings.DESCRIPTION),
            version=str(settings.VERSION),
            license_info=settings.LICENCE_INFO,
        )

        # Attach middlewares
        server.middleware("http")(trailing_slash_handler_middleware)
        # server.middleware("http")(log_requests_middleware)

        # Attach routes
        server.include_router(router=upload.router)
        server.include_router(router=get_files_list.router)
        server.include_router(router=get_file.router)
        server.include_router(router=delete.router)

        logger.info(f"Server created.")

        return server

    def run_server(self, port: int = int(settings.SERVER_PORT), host: str = settings.SERVER_HOST):
        """
        Starts the FastAPI server.

        Logs the server startup information and runs the server using Uvicorn.

        Args:
            port (int): The port on which the server will run. Defaults to NLG_SERVER_PORT.
            host (str): The host on which the server will listen. Defaults to NLG_SERVER_HOST.
        """
        logger.info(f"Starting server on http//{host}:{port}")
        uvicorn.run(self.server, host=host, port=port)
        logger.info("Server shutdown complete.")
