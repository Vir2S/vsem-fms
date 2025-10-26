import uvicorn
from fastapi import FastAPI

from vsem_fms.app.config import settings
from vsem_fms.app.constants import DOCS_URL, OPENAPI_URL, REDOC_URL, ROOT_API
from vsem_fms.app.core.logging import logger
from vsem_fms.app.middlewares.log_requests_middleware import log_requests_middleware
from vsem_fms.app.middlewares.slash_trailing_middleware import trailing_slash_handler_middleware
from vsem_fms.app.routes import delete, get_file, get_files_list, ping, upload


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

    def __create_server(self) -> FastAPI:
        """
        Configures the FastAPI server with the necessary routes.

        This method attaches predefined routers to the server instance.

        Returns:
            FastAPI: Configured FastAPI server.
        """
        # Initialize FastAPI with metadata
        server = FastAPI(
            title=str(settings.TITLE),
            docs_url=DOCS_URL,
            redoc_url=REDOC_URL,
            openapi_url=OPENAPI_URL,
            description=str(settings.DESCRIPTION),
            version=str(settings.VERSION),
            license_info=settings.LICENCE_INFO,
        )
        self._setup_middlewares(app=server)
        self._register_routes(app=server)

        logger.info("Server initialized", extra={"title": settings.TITLE, "version": settings.VERSION})

        return server

    def _setup_middlewares(self, app: FastAPI) -> None:
        """
        Attaches middlewares to the FastAPI app.

        Args:
            app (FastAPI): The FastAPI application instance.
        """
        app.middleware("http")(trailing_slash_handler_middleware)
        app.middleware("http")(log_requests_middleware)

    def _register_routes(self, app: FastAPI) -> None:
        """
        Includes routers into the FastAPI app.

        Args:
            app (FastAPI): The FastAPI application instance.
        """
        routers = [
            upload.router,
            get_files_list.router,
            get_file.router,
            delete.router,
            ping.router,
        ]
        for router in routers:
            app.include_router(router, prefix=ROOT_API)

    def run_server(self, port: int = int(settings.SERVER_PORT), host: str = settings.SERVER_HOST):
        """
        Starts the FastAPI server.

        Logs the server startup information and runs the server using Uvicorn.

        Args:
            port (int): The port on which the server will run. Defaults to NLG_SERVER_PORT.
            host (str): The host on which the server will listen. Defaults to NLG_SERVER_HOST.
        """
        logger.info(f"Starting server on http://{host}:{port}")
        uvicorn.run(self.server, host=host, port=port)
        logger.info("Server shutdown complete.")
