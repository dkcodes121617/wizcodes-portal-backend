"""Shared test fixtures.

Tests must not depend on a developer's local machine, so the environment is
populated here before the app imports its settings.
"""

from __future__ import annotations

import os

import pytest

# ENVIRONMENT is deliberately NOT set here: the app detects it, and pinning it
# would hide that detection from the tests that exercise it.
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-used-in-any-real-environment")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://test:test@localhost:5432/test?sslmode=disable",
)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
