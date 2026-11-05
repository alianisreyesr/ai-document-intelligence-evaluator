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


def test_api_preserves_ranked_retrieval_and_version_metadata():
    payload = _evaluation_payload(
        provider="open-source",
        model_version="model-a-v1",
        prompt_version="prompt-v2",
        retriever_version="bm25-v1",
        candidate={
            "answer": "Returns are accepted within 30 days.",
            "citations": ["DOC-1"],
            "retrieved_document_ids": ["DOC-NOISE", "DOC-1"],
            "latency_ms": 200,
            "cost_usd": 0.001,
        },
    )
    body = client.post("/api/evaluations", json=payload).json()
    assert body["metrics"]["retrieval_mrr"] == 0.5
    assert body["provider"] == "open-source"
    assert body["evaluation_id"].startswith("EVAL-")


def test_history_and_model_comparison_capture_runs():
    client.post("/api/evaluations", json=_evaluation_payload(provider="provider-a", model_version="v1"))
    history = client.get("/api/evaluations/history?limit=1").json()
    assert history["count"] == 1
    assert history["storage"] == "bounded-process-memory"

    comparison = client.get("/api/experiments/compare").json()
    assert any(model["provider"] == "provider-a" and model["runs"] >= 1 for model in comparison["models"])


def test_threshold_overrides_reject_out_of_range_values():
    for field, value in [
        ("citation_validity", 1.5),
        ("groundedness", -0.1),
        ("latency_ms", -1),
        ("cost_usd", -0.01),
        ("retrieval_mrr", "nan"),
    ]:
        payload = _evaluation_payload(thresholds={field: value})
        assert client.post("/api/evaluations", json=payload).status_code == 422, field


def test_threshold_overrides_accept_boundaries():
    payload = _evaluation_payload(thresholds={"citation_validity": 0, "groundedness": 1, "latency_ms": 0, "cost_usd": 0})
    assert client.post("/api/evaluations", json=payload).status_code == 200


def test_oversized_inputs_are_rejected():
    too_many = [{"id": f"D{i}", "text": "x"} for i in range(101)]
    assert client.post("/api/evaluations", json=_evaluation_payload(documents=too_many)).status_code == 422
    long_text = [{"id": "DOC-1", "text": "x" * 50_001}]
    assert client.post("/api/evaluations", json=_evaluation_payload(documents=long_text)).status_code == 422


def test_oversized_body_gets_413():
    response = client.post(
        "/api/evaluations",
        content=b"{" + b" " * 1_100_000 + b"}",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 413


def test_empty_expected_lists_report_na_not_perfect_scores():
    payload = _evaluation_payload(expected_document_ids=[], required_facts=[])
    body = client.post("/api/evaluations", json=payload).json()
    metrics = body["metrics"]
    assert metrics["evidence_coverage"] is None
    assert metrics["retrieval_recall_at_k"] is None
    assert metrics["required_fact_recall"] is None


def test_duplicate_document_ids_are_rejected_with_422():
    payload = _evaluation_payload(
        documents=[
            {"id": "DOC-1", "text": "Returns are accepted within 30 days."},
            {"id": "DOC-1", "text": "A conflicting duplicate."},
        ]
    )
    response = client.post("/api/evaluations", json=payload)
    assert response.status_code == 422
    assert "Duplicate document ids" in response.text


def test_api_recall_at_k_truncates_ranking():
    payload = _evaluation_payload(
        k=1,
        candidate={
            "answer": "Returns are accepted within 30 days.",
            "citations": ["DOC-1"],
            "retrieved_document_ids": ["DOC-NOISE", "DOC-1"],
            "latency_ms": 200,
            "cost_usd": 0.001,
        },
    )
    body = client.post("/api/evaluations", json=payload).json()
    assert body["metrics"]["retrieval_recall_at_k"] == 0.0
    assert body["metrics"]["retrieval_mrr"] == 0.5


def test_api_rejects_invalid_k():
    for k in (0, -1, 101):
        assert client.post("/api/evaluations", json=_evaluation_payload(k=k)).status_code == 422
