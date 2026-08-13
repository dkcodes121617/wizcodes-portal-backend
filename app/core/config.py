"""Application settings.

Everything is read from environment variables (12-factor). A local ``.env`` is
loaded as a convenience for development; on Render the real process environment
always wins and no ``.env`` is deployed.

The guiding rule here is: **a developer should have to set exactly one variable
locally (DATABASE_URL), and everything else should figure itself out.**

    Running on Render?   -> ENVIRONMENT=production, DEBUG/RELOAD off
    Running anywhere else -> ENVIRONMENT=development, DEBUG/RELOAD on

Any of those can still be overridden explicitly; the detection only supplies
defaults. Production additionally refuses to start with unsafe values, so a
misconfiguration fails loudly at boot instead of quietly at 3am.
"""

from __future__ import annotations

import os
import secrets
from functools import lru_cache
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "staging", "production"]


def detect_environment() -> Environment:
    """Infer the environment from the host platform.

    Render injects RENDER=true and RENDER_SERVICE_ID into every service, so a
    deployed process identifies itself without anyone remembering to set a flag.
    """
    if os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID"):
        return "production"
    return "development"


def detect_public_base_url() -> str:
    """Render publishes the service's own external URL; used for keep-alive."""
    return (os.getenv("RENDER_EXTERNAL_URL") or "").rstrip("/")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- app ---
    PROJECT_NAME: str = "WizCodes Portal API"
    ENVIRONMENT: Environment = Field(default_factory=detect_environment)
    DEBUG: bool = False  # replaced by the environment default below
    API_V1_PREFIX: str = "/api/v1"

    # --- server (Render injects PORT; HOST stays externally reachable) ---
    HOST: str = "0.0.0.0"  # noqa: S104 - must bind all interfaces for containers
    PORT: int = 8000
    RELOAD: bool = False  # replaced by the environment default below
    LOG_LEVEL: str = "INFO"

    # --- security ---
    # Auto-generated for local development. Production requires an explicit
    # value, otherwise every restart would invalidate previously issued tokens.
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    ENABLE_DOCS: bool = True

    # --- CORS ---
    # Wildcard by explicit request. NOTE: the browser spec forbids pairing "*"
    # with credentialed requests, so cookie-based auth would need a real
    # allow-list. Bearer tokens in the Authorization header work fine with "*".
    CORS_ORIGINS: str = "*"
    CORS_ALLOW_CREDENTIALS: bool = False

    # --- the single frontend <-> backend link ---
    # Frontend reads NEXT_PUBLIC_API_URL; backend reads FRONTEND_URL. Both name
    # the same connection. Informational here, since CORS is already wildcard.
    FRONTEND_URL: str = "http://localhost:3000"

    # --- keep-alive (Render free tier sleeps after ~15 min idle) ---
    KEEPALIVE_ENABLED: bool = True
    KEEPALIVE_INTERVAL_SECONDS: int = 840  # 14 minutes, just under the 15 min cutoff
    PUBLIC_BASE_URL: str = Field(default_factory=detect_public_base_url)

    # --- database (Neon Postgres 18) ---
    DATABASE_URL: str
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_RECYCLE_SECONDS: int = 300  # Neon drops idle connections
    DB_ECHO: bool = False

    # ------------------------------------------------------------------
    # validation
    # ------------------------------------------------------------------

    @model_validator(mode="before")
    @classmethod
    def _apply_environment_defaults(cls, data: Any) -> Any:
        """Derive DEBUG/RELOAD from the environment unless set explicitly."""
        if not isinstance(data, dict):
            return data

        environment = data.get("ENVIRONMENT") or detect_environment()
        data["ENVIRONMENT"] = environment
        is_production = environment == "production"

        data.setdefault("DEBUG", not is_production)
        data.setdefault("RELOAD", not is_production)
        return data

    @field_validator("DATABASE_URL")
    @classmethod
    def _require_database_url(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("DATABASE_URL must be set")
        return value.strip()

    @field_validator("LOG_LEVEL")
    @classmethod
    def _normalise_log_level(cls, value: str) -> str:
        level = value.strip().upper()
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        if level not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(allowed)}")
        return level

    @field_validator("PUBLIC_BASE_URL", "FRONTEND_URL")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.strip().rstrip("/")

    @model_validator(mode="after")
    def _guard_production(self) -> Settings:
        if not self.is_production:
            return self

        if self.DEBUG:
            raise ValueError("DEBUG must be false in production")
        if self.RELOAD:
            raise ValueError("RELOAD must be false in production")
        if "SECRET_KEY" not in self.model_fields_set:
            raise ValueError(
                "SECRET_KEY must be set explicitly in production. Without it a "
                "fresh key is generated on every restart, invalidating all "
                "previously issued tokens."
            )
        return self

    # ------------------------------------------------------------------
    # derived values
    # ------------------------------------------------------------------

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def cors_origins(self) -> list[str]:
        """Parsed CORS allow-list. ``*`` stays a single wildcard entry."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def keepalive_active(self) -> bool:
        """Self-ping only makes sense for a deployed service with a public URL."""
        return self.KEEPALIVE_ENABLED and self.is_production and bool(self.PUBLIC_BASE_URL)

    def _dsn_with_driver(self, driver: str) -> str:
        """Rewrite the Neon DSN onto an explicit SQLAlchemy driver.

        Neon hands out ``postgresql://...?sslmode=require``. SQLAlchemy needs the
        driver spelled out, and psycopg3 understands ``sslmode`` natively, so the
        query string is preserved as-is.
        """
        parts = urlsplit(self.DATABASE_URL)
        scheme = parts.scheme.split("+", 1)[0]
        if scheme not in {"postgres", "postgresql"}:
            raise ValueError(f"Unsupported DATABASE_URL scheme: {parts.scheme!r}")
        return urlunsplit((driver, parts.netloc, parts.path, parts.query, parts.fragment))

    @property
    def async_database_url(self) -> str:
        return self._dsn_with_driver("postgresql+psycopg")

    @property
    def sync_database_url(self) -> str:
        """Used by the migration runner, which connects synchronously."""
        return self._dsn_with_driver("postgresql+psycopg")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton — env is read once per process."""
    return Settings()  # type: ignore[call-arg]
