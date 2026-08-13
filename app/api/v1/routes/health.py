"""Liveness and readiness probes.

``/health`` answers without touching the database so Render's health check keeps
passing during a transient Neon blip; ``/health/ready`` is the one that proves
the database round-trips.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.schemas.common import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        service=settings.PROJECT_NAME,
        environment=settings.ENVIRONMENT,
        version="1.0.0",
    )


@router.get("/health/ready", response_model=ReadinessResponse, summary="Readiness probe")
async def readiness(
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> ReadinessResponse:
    started = time.perf_counter()
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:  # a probe reports failure, it never raises
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(status="degraded", database="down", detail=str(exc)[:200])

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return ReadinessResponse(status="ok", database="up", latency_ms=elapsed_ms)
