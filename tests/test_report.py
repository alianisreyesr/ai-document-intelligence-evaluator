import json
from pathlib import Path

from app.report import evaluate_batch, export_report


DATA = Path(__file__).parents[1] / "data" / "evaluation_cases.json"


def test_batch_report_aggregates_failures():
    report = evaluate_batch(json.loads(DATA.read_text()))
    assert report["summary"] == {"total": 2, "passed": 1, "failed": 1, "pass_rate": 0.5}
    assert report["failure_counts"]["citation_validity"] == 1
    assert report["averages"]["latency_ms"] == 850.0


def test_report_exports_html_and_json(tmp_path: Path):
    output = tmp_path / "evaluation-dashboard.html"
    report = export_report(DATA, output)
    assert report["summary"]["total"] == 2
    assert "AI Quality Dashboard" in output.read_text()
    assert output.with_suffix(".json").exists()
