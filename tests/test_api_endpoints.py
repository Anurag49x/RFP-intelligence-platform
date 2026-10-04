"""API integration tests for all FastAPI endpoints."""

from fastapi.testclient import TestClient
import pytest
from app.api.main import app

client = TestClient(app)


def test_api_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_api_search_get():
    resp = client.get("/search", params={"q": "laptop dell", "bid_id": "Bid2", "top_k": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert len(data["results"]) >= 1


def test_api_search_post():
    resp = client.post(
        "/search",
        json={"query": "laptop due date", "filters": {"bid_id": "Bid1"}, "top_k": 3},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data


def test_api_extract_endpoint():
    resp = client.post("/extract", json={"bid_id": "Bid2"})
    assert resp.status_code == 200
    data = resp.json()
    assert "Bid Number" in data
    assert "Due Date" in data
    assert "Model_no" in data


def test_api_ask_endpoint():
    resp = client.post("/ask", json={"question": "What is the final deadline for Bid1?", "bid_id": "Bid1"})
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "citations" in data
    assert data["validation_status"] in ["passed", "repaired"]
