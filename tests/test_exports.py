import csv
import io
from fastapi.testclient import TestClient
from app import history
from app.main import app, DEMO_CASES


def test_dates_exports_and_escaping():
    with TestClient(app) as client:
        row = client.post("/api/evaluations", json={**DEMO_CASES[0], "provider": "=1+1",
                                                  "model_version": "<script>alert(1)</script>"}).json()
        day = row["evaluated_at"][:10]
        assert client.get("/api/evaluations/history", params={"date_from": day, "date_to": day}).json()["total"] == 1
        assert client.get("/api/evaluations/history?date_to=2000-01-01").json()["total"] == 0
        assert client.get("/api/evaluations/history?date_from=2030-01-01&date_to=2000-01-01").status_code == 422
        assert client.get("/api/evaluations/history?date_from=garbage").status_code == 422
        exported = client.get("/api/evaluations/export", params={"date_from": day, "provider": "=1+1"})
        parsed = list(csv.DictReader(io.StringIO(exported.text)))
        assert parsed[0]["provider"] == "'=1+1"
        assert parsed[0]["run_id"] == row["run_id"]
        page = client.get("/history").text
        assert "<script>alert(1)</script>" not in page
        assert "&lt;script&gt;" in page
        assert client.get("/api/evaluations/export?provider=missing").text.count("\n") == 1


def test_utc_boundary():
    history.save({"evaluated_at": "2026-01-02T00:30:00+02:00", "provider": "test"})
    with TestClient(app) as client:
        assert client.get("/api/evaluations/history?date_to=2026-01-01").json()["total"] == 1
