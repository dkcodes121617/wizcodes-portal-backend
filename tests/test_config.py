"""Environment auto-detection and the production safety guards.

These are the rules that keep local development effortless without letting a
misconfigured production deploy start.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings, detect_environment


@pytest.fixture(autouse=True)
def _clear_render_markers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("RENDER_SERVICE_ID", raising=False)
    monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)


def test_detects_development_off_render() -> None:
    assert detect_environment() == "development"


def test_detects_production_on_render(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RENDER", "true")
    assert detect_environment() == "production"


def test_development_enables_debug_and_reload() -> None:
    settings = Settings()
    assert settings.ENVIRONMENT == "development"
    assert settings.DEBUG is True
    assert settings.RELOAD is True


def test_production_disables_debug_and_reload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RENDER", "true")
    settings = Settings()
    assert settings.is_production
    assert settings.DEBUG is False
    assert settings.RELOAD is False


def test_production_requires_an_explicit_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings()


def test_production_rejects_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("DEBUG", "true")

    with pytest.raises(ValidationError, match="DEBUG"):
        Settings()


def test_neon_dsn_gets_an_explicit_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:pw@ep-test.us-east-2.aws.neon.tech/neondb?sslmode=require",
    )
    settings = Settings()

    # The driver is named explicitly and the sslmode query survives untouched.
    assert settings.async_database_url.startswith("postgresql+psycopg://")
    assert settings.async_database_url.endswith("?sslmode=require")


def test_cors_wildcard_is_a_single_entry() -> None:
    settings = Settings()
    assert settings.cors_origins == ["*"]


def test_keepalive_is_inert_locally() -> None:
    # No public URL and not production -> nothing should ping.
    assert Settings().keepalive_active is False


def test_keepalive_activates_on_render(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://example.onrender.com/")
    settings = Settings()

    assert settings.keepalive_active is True
    # Trailing slash stripped so path joins never double up.
    assert settings.PUBLIC_BASE_URL == "https://example.onrender.com"
