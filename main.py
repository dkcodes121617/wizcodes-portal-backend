"""Entrypoint.

    venv\\Scripts\\activate
    python main.py

Binds 0.0.0.0 so the server is reachable from outside the machine/container, on
the port given by the PORT environment variable (Render injects this).
"""

from __future__ import annotations

import asyncio
import sys

import uvicorn

from app.core.config import Settings, get_settings

APP_PATH = "app.main:app"


def _build_config(settings: Settings) -> uvicorn.Config:
    return uvicorn.Config(
        APP_PATH,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        # Render terminates TLS at its proxy; trust the forwarded headers so
        # request.url.scheme is https and HSTS is emitted correctly.
        proxy_headers=True,
        forwarded_allow_ips="*",
        access_log=True,
        server_header=False,  # do not advertise the server software
        date_header=True,
    )


def main() -> None:
    settings = get_settings()

    if settings.RELOAD:
        # The reload supervisor has to own the process tree, so hand off to
        # uvicorn.run. Its subprocess path already picks a psycopg-compatible
        # event loop on every platform.
        uvicorn.run(
            APP_PATH,
            host=settings.HOST,
            port=settings.PORT,
            reload=True,
            log_level=settings.LOG_LEVEL.lower(),
            proxy_headers=True,
            forwarded_allow_ips="*",
        )
        return

    # Single-process path. uvicorn would otherwise force a ProactorEventLoop on
    # Windows, which psycopg's async driver cannot use; running the server on a
    # loop we create ourselves keeps local dev and Render on the same code path.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    server = uvicorn.Server(_build_config(settings))
    asyncio.run(server.serve())


if __name__ == "__main__":
    main()
