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


def _evaluation_payload(**overrides) -> dict:
    payload = {
        "case_id": "CASE-TEST",
        "documents": [{"id": "DOC-1", "text": "Returns are accepted within 30 days."}],
        "expected_document_ids": ["DOC-1"],
        "required_facts": ["30 days"],
        "candidate": {
            "answer": "Returns are accepted within 30 days.",
            "citations": ["DOC-1"],
            "latency_ms": 2000,
            "cost_usd": 0.0018,
        },
    }
    payload.update(overrides)
    return payload


def test_evaluation_uses_default_thresholds_when_none_given():
    response = client.post("/api/evaluations", json=_evaluation_payload())
    assert response.status_code == 200
    body = response.json()
    # latency_ms=2000 exceeds the default 1500ms threshold.
    assert "latency_ms" in body["failures"]
    assert body["passed"] is False


def test_evaluation_accepts_custom_thresholds():
    """GET /api/thresholds advertises these as configurable; POST
    /api/evaluations must actually honor an override, not silently score
    against the default regardless of what's supplied."""
    payload = _evaluation_payload(thresholds={"latency_ms": 5000})
    response = client.post("/api/evaluations", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "latency_ms" not in body["failures"]
    assert body["passed"] is True


def test_evaluation_threshold_override_is_partial():
    """Only the overridden field changes; every other threshold still uses
    its default value from Thresholds()."""
    payload = _evaluation_payload(
        thresholds={"latency_ms": 5000},
        candidate={
            "answer": "Returns are accepted within 30 days.",
            "citations": ["DOC-1", "DOC-DOES-NOT-EXIST"],
            "latency_ms": 2000,
            "cost_usd": 0.0018,
        },
    )
    response = client.post("/api/evaluations", json=payload)
    body = response.json()
    assert "latency_ms" not in body["failures"]  # overridden to 5000ms, 2000ms passes
    assert "citation_validity" in body["failures"]  # default 1.0 still enforced
