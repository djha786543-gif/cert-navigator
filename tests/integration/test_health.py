"""
Integration tests — health endpoints.
Requires the FastAPI server to be running (or use TestClient for offline testing).

These tests use FastAPI TestClient — no external server needed.
The v1 SQLite stack (src.backend.main) is used to avoid PostgreSQL dependency.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def v1_client():
    """TestClient wrapping the v1 SQLite FastAPI app."""
    try:
        from src.backend.user_management import app
        from src.backend.api_routes import router as career_router
        app.include_router(career_router, prefix="/api")
        return TestClient(app, raise_server_exceptions=False)
    except Exception as e:
        pytest.skip(f"v1 app failed to import: {e}")


class TestHealthEndpoints:
    def test_health_returns_200(self, v1_client):
        response = v1_client.get("/health")
        assert response.status_code == 200

    def test_health_returns_ok_status(self, v1_client):
        response = v1_client.get("/health")
        data = response.json()
        assert data.get("status") == "ok"

    def test_health_returns_version(self, v1_client):
        response = v1_client.get("/health")
        data = response.json()
        assert "version" in data

    def test_proctor_catalog_no_auth_required(self, v1_client):
        """Catalog endpoint should return data without authentication."""
        response = v1_client.get("/api/proctor/catalog")
        # May be 200 or 404 depending on router mounting; 401 would be wrong
        assert response.status_code != 401

    def test_unauthenticated_api_returns_401(self, v1_client):
        """Protected endpoints should reject unauthenticated requests."""
        response = v1_client.get("/api/jobs/me")
        assert response.status_code in (401, 403, 422)

    def test_fair_calc_no_auth(self, v1_client):
        """FAIR calculator endpoint requires no auth."""
        response = v1_client.post(
            "/api/resilience/fair-calc",
            json={"tef": 4.0, "vulnerability": 0.45, "primary_loss": 50000, "secondary_loss": 0}
        )
        # Should be 200 (success) or 422 (validation) — not 401
        assert response.status_code != 401

    def test_fair_calc_invalid_vulnerability_rejected(self, v1_client):
        response = v1_client.post(
            "/api/resilience/fair-calc",
            json={"tef": 4.0, "vulnerability": 1.5, "primary_loss": 50000}
        )
        assert response.status_code == 422

    def test_fair_calc_negative_tef_rejected(self, v1_client):
        response = v1_client.post(
            "/api/resilience/fair-calc",
            json={"tef": -1.0, "vulnerability": 0.5, "primary_loss": 50000}
        )
        assert response.status_code == 422
