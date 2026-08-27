import uvicorn
from fastapi import FastAPI

from vsem_fms.app.config import settings
from vsem_fms.app.constants import DOCS_URL, OPENAPI_URL, REDOC_URL, ROOT_API
from vsem_fms.app.core.logging import logger
from vsem_fms.app.middlewares.log_requests_middleware import log_requests_middleware
from vsem_fms.app.middlewares.slash_trailing_middleware import trailing_slash_handler_middleware
from vsem_fms.app.routes import delete, get_file, get_files_list, ping, upload


class Server:
    """Configure and run the FastAPI application."""

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
            license_info=settings.LICENSE_INFO,
        )
        self._setup_middlewares(app=server)
        self._register_routes(app=server)
        logger.info(f"Server initialized: {settings.TITLE} v{settings.VERSION}")
        return server

    def _setup_middlewares(self, app: FastAPI) -> None:
        app.middleware("http")(trailing_slash_handler_middleware)
        app.middleware("http")(log_requests_middleware)

    def _register_routes(self, app: FastAPI) -> None:
        for router in (
            upload.router,
            get_files_list.router,
            get_file.router,
            delete.router,
            ping.router,
        ):
            app.include_router(router, prefix=ROOT_API)

    def run_server(
        self,
        port: int = settings.SERVER_PORT,
        host: str = settings.SERVER_HOST,
    ) -> None:
        logger.info(f"Starting server on http://{host}:{port}")
        uvicorn.run(self.server, host=host, port=port)
