import json
from pathlib import Path

from app.report import evaluate_batch, export_report, render_dashboard
from app.report import main as report_main

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


def test_batch_report_handles_na_metrics():
    from app.report import evaluate_batch, render_dashboard
    from tests.test_evaluator import CASES

    case = {**CASES[0], "expected_document_ids": [], "required_facts": []}
    report = evaluate_batch([case])
    assert report["averages"]["evidence_coverage"] is None
    assert "N/A" in render_dashboard(report)


def test_render_dashboard_escapes_html_in_case_ids():
    from tests.test_evaluator import CASES

    case = {**CASES[0], "case_id": "<script>alert(1)</script>&"}
    html_output = render_dashboard(evaluate_batch([case]))
    assert "<script>alert(1)</script>" not in html_output
    assert "&lt;script&gt;alert(1)&lt;/script&gt;&amp;" in html_output


def test_report_main_writes_outputs(tmp_path: Path, capsys):
    output = tmp_path / "out" / "dashboard.html"
    report_main(["--input", str(DATA), "--output", str(output)])
    assert output.exists()
    assert "total=2 pass_rate=50%" in capsys.readouterr().out
