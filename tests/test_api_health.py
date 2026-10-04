"""Tests for FastAPI health check endpoint and configuration loading."""

from fastapi.testclient import TestClient
from app.config import get_settings


def test_health_check_endpoint(test_client: TestClient):
    """Test that the /health endpoint returns 200 and expected status."""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app_env" in data
    assert "version" in data


def test_settings_load_without_credentials():
    """Verify settings can be loaded cleanly even without optional API keys."""
    settings = get_settings()
    assert settings.app_env in {"development", "production", "test"}
    assert settings.qdrant_url is not None and len(settings.qdrant_url) > 0
