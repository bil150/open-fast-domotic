import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.container import build_container
from app.core.errors import AppError
from app.core.logging import setup_logging
from app.protocols.base import BaseCoordinator

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, coordinators: list[BaseCoordinator] | None = None) -> FastAPI:
    settings = settings or get_settings()
    container = build_container(settings, coordinators)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        setup_logging(settings.log_file)
        logger.info("open-fast-domotic %s - GPL-3.0 licensed - by @bil150", settings.version)
        await container.start()
        logger.info("System is fully initialized")
        yield
        logger.info("Server is shutting down")
        await container.stop()

    app = FastAPI(title="open-fast-domotic", version=settings.version, lifespan=lifespan)
    app.state.container = container

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, error: AppError) -> JSONResponse:
        return JSONResponse(status_code=error.status_code, content={"detail": error.message})

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/api/v1", tags=["info"])
    def info() -> dict[str, str]:
        return {"name": "open-fast-domotic", "version": settings.version, "docs": "/docs"}

    # Serve the built client (same origin as the API) when STATIC_DIR points to it.
    if settings.static_dir and os.path.isdir(settings.static_dir):
        app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="client")

    return app
