import uvicorn
from fastapi import FastAPI

from vsem_fms.app.config import settings
from vsem_fms.app.constants import DOCS_URL, OPENAPI_URL, REDOC_URL, ROOT_API
from vsem_fms.app.core.logging import logger
from vsem_fms.app.middlewares.log_requests_middleware import log_requests_middleware
from vsem_fms.app.middlewares.slash_trailing_middleware import trailing_slash_handler_middleware
from vsem_fms.app.routes import delete, get_file, get_files_list, ping, upload


class Server:
    """Configure and run the FastAPI server."""

    def __init__(self) -> None:
        self.server = self.__create_server()

    def __create_server(self) -> FastAPI:
        server = FastAPI(
            title=settings.TITLE,
            docs_url=DOCS_URL,
            redoc_url=REDOC_URL,
            openapi_url=OPENAPI_URL,
            description=settings.DESCRIPTION,
            version=settings.VERSION,
            contact=settings.CONTACT,
            license_info=settings.LICENCE_INFO,
        )
        self._setup_middlewares(server)
        self._register_routes(server)
        logger.info("Server initialized: {} {}", settings.TITLE, settings.VERSION)
        return server

    def _setup_middlewares(self, app: FastAPI) -> None:
        app.middleware("http")(trailing_slash_handler_middleware)
        app.middleware("http")(log_requests_middleware)

    def _register_routes(self, app: FastAPI) -> None:
        for router in [upload.router, get_files_list.router, get_file.router, delete.router, ping.router]:
            app.include_router(router, prefix=ROOT_API)

    def run_server(self, port: int | None = None, host: str | None = None) -> None:
        server_port = port if port is not None else settings.SERVER_PORT
        server_host = host if host is not None else settings.SERVER_HOST
        logger.info("Starting server on http://{}:{}", server_host, server_port)
        uvicorn.run(self.server, host=server_host, port=server_port)
