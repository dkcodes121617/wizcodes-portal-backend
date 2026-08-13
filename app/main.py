"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core import keepalive
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.db.session import dispose_engine

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    logger.info(
        "Starting %s (env=%s) on %s:%s",
        settings.PROJECT_NAME,
        settings.ENVIRONMENT,
        settings.HOST,
        settings.PORT,
    )

    # Prevents the Render free tier from idling out. No-op off Render.
    keepalive_task = keepalive.start(settings)

    yield

    await keepalive.stop(keepalive_task)
    await dispose_engine()
    logger.info("Shutdown complete; database pool disposed.")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    docs_enabled = settings.ENABLE_DOCS
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="Backend API for the WizCodes portal.",
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    app.state.settings = settings

    # --- middleware (outermost first) ---
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # CORS is wildcard by configuration. Credentials must stay off for "*" to be
    # honoured by browsers; bearer tokens in the Authorization header still work.
    allow_origins = settings.cors_origins
    allow_credentials = settings.CORS_ALLOW_CREDENTIALS and "*" not in allow_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time-ms"],
        max_age=600,
    )

    # --- routes ---
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Unprefixed liveness route: Render's health check points here.
    @app.get("/health", tags=["health"], include_in_schema=False)
    async def root_health() -> dict[str, str]:
        return {"status": "ok"}

    # Target for the anti-idle ping (self-ping every 14 min, plus the GitHub
    # Actions cron). Deliberately does no work — it exists purely to be cheap
    # traffic that resets Render's idle timer.
    @app.get("/keepalive", tags=["health"], include_in_schema=False)
    async def keepalive_probe() -> dict[str, str]:
        return {"status": "awake"}

    @app.get("/", tags=["meta"], include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "service": settings.PROJECT_NAME,
            "environment": settings.ENVIRONMENT,
            "docs": "/docs" if docs_enabled else "disabled",
            "api": settings.API_V1_PREFIX,
        }

    # --- error handling: never leak internals to the client ---
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Request validation failed.",
                "errors": exc.errors(),
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.exception("Unhandled error [request_id=%s]", request_id)
        detail = str(exc) if settings.DEBUG else "Internal server error."
        return JSONResponse(status_code=500, content={"detail": detail, "request_id": request_id})

    return app


app = create_app()
