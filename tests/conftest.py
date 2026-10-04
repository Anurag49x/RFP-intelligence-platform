"""Pytest configuration and shared fixtures for RFP Intelligence Platform."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.config import Settings, get_settings


@pytest.fixture
def test_client() -> TestClient:
    """FastAPI TestClient instance."""
    return TestClient(app)


@pytest.fixture
def project_root() -> Path:
    """Root directory of the project."""
    return Path(__file__).parent.parent.resolve()


@pytest.fixture
def data_dir(project_root: Path) -> Path:
    """Data directory containing Bid1 and Bid2."""
    return project_root / "data"


@pytest.fixture
def bid1_path(data_dir: Path) -> Path:
    """Path to Bid1 folder."""
    return data_dir / "Bid1"


@pytest.fixture
def bid2_path(data_dir: Path) -> Path:
    """Path to Bid2 folder."""
    return data_dir / "Bid2"
