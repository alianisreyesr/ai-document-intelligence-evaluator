from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_dashboard_exposes_quality_evidence():
    response = client.get("/")
    assert response.status_code == 200
    assert "AI Quality Dashboard" in response.text
    assert "Failure diagnostics" in response.text


def test_health_requires_human_review():
    response = client.get("/health")
    assert response.status_code == 200
    assert "human review" in response.json()["ai_boundary"]


def test_thresholds_are_transparent():
    response = client.get("/api/thresholds")
    assert response.status_code == 200
    assert response.json()["citation_validity"] == 1.0
