from app import history
from fastapi.testclient import TestClient
from app.main import app, DEMO_CASES


def test_duplicate_fingerprints_have_distinct_runs():
    a = history.save({"evaluation_id": "same"})
    b = history.save({"evaluation_id": "same"})
    assert a["run_id"] != b["run_id"]
    assert history.get(a["run_id"]) == a
    assert len(history.records()) == 2


def test_reopen_database_preserves_runs():
    saved = history.save({"value": 1})
    with history.connection() as conn:
        assert conn.execute("SELECT version FROM schema_versions").fetchall() == [(1,)]
    assert history.get(saved["run_id"]) == saved


def test_regression_direction_and_filters():
    with TestClient(app) as client:
        payload = {**DEMO_CASES[0], "model_version": "baseline"}
        first = client.post("/api/evaluations", json=payload).json()
        payload = {**payload, "model_version": "candidate",
                   "candidate": {**payload["candidate"], "latency_ms": 9999}}
        second = client.post("/api/evaluations", json=payload).json()
        result = client.get("/api/experiments/regressions", params={"baseline": first["run_id"], "candidate": second["run_id"]})
        assert result.status_code == 200
        assert result.json()["regressions"] == ["latency_ms"]
        assert client.get("/api/evaluations/history", params={"model_version": "candidate"}).json()["total"] == 1
        assert client.get("/api/evaluations/runs/missing").status_code == 404


def test_incompatible_evidence_rejected():
    with TestClient(app) as client:
        a = client.post("/api/evaluations", json=DEMO_CASES[0]).json()
        b = client.post("/api/evaluations", json=DEMO_CASES[1]).json()
        assert client.get("/api/experiments/regressions", params={"baseline": a["run_id"], "candidate": b["run_id"]}).status_code == 422
