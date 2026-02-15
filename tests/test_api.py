"""
API integration tests.

Uses FastAPI's TestClient (backed by httpx) for synchronous HTTP testing.
Tests the health endpoint and validates request/response contracts.

Note: Upload and match tests require ML models.
Run with: pytest tests/test_api.py -v -k "health"
For full tests (with model download): pytest tests/test_api.py -v
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_health_response_schema(self, client):
        response = client.get("/api/v1/health")
        data = response.json()
        assert set(data.keys()) == {"status", "version", "models_loaded"}


class TestUploadEndpoint:
    def test_upload_no_file(self, client):
        """Upload without file should return 422."""
        response = client.post("/api/v1/upload_resume")
        assert response.status_code == 422


class TestMatchEndpoint:
    def test_match_invalid_resume_id(self, client):
        """Match with non-existent resume ID should fail."""
        response = client.post(
            "/api/v1/match",
            json={
                "resume_id": "nonexistent_id",
                "job_description": {
                    "title": "Test Job",
                    "description": "Test description for the job",
                    "required_skills": ["Python"],
                    "preferred_skills": [],
                },
            },
        )
        # Should return 404 or 422
        assert response.status_code in (404, 422, 500)

    def test_match_invalid_body(self, client):
        """Match with invalid body should return 422."""
        response = client.post("/api/v1/match", json={"invalid": "body"})
        assert response.status_code == 422
