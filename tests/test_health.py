"""Smoke tests for the probes and the wildcard CORS configuration.

These deliberately avoid the database so CI needs no live Neon connection.
"""

from __future__ import annotations


def test_root_health_is_ok(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_versioned_health_reports_service_metadata(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "development"
    assert body["service"]


def test_keepalive_probe_responds(client) -> None:
    response = client.get("/keepalive")
    assert response.status_code == 200
    assert response.json() == {"status": "awake"}


def test_request_id_header_is_returned(client) -> None:
    response = client.get("/health")
    assert response.headers.get("X-Request-ID")


def test_security_headers_are_present(client) -> None:
    response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_cors_allows_any_origin(client) -> None:
    response = client.get("/health", headers={"Origin": "https://example.com"})
    assert response.headers["access-control-allow-origin"] == "*"


def test_cors_preflight_is_permitted(client) -> None:
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "https://wizcodes-portal-frontend.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
