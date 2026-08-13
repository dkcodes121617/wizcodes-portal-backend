"""Response envelopes shared across routes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    environment: str
    version: str


class ReadinessResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["up", "down"]
    latency_ms: float | None = None
    detail: str | None = None


class ErrorResponse(BaseModel):
    detail: str = Field(description="Human-readable error message")
    request_id: str | None = None
