import json
from pathlib import Path

import pytest

from app.cli import main

DATA = Path(__file__).parents[1] / "data" / "evaluation_cases.json"


def test_cli_prints_one_line_per_case(capsys):
    assert main([str(DATA)]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("CASE-001 PASS citation_validity=1.00")
    assert lines[1].startswith("CASE-002 FAIL")


def test_cli_defaults_to_bundled_dataset(capsys, monkeypatch):
    monkeypatch.chdir(DATA.parents[1])
    assert main([]) == 0
    assert "CASE-001" in capsys.readouterr().out


def test_cli_uses_sys_argv_when_called_without_arguments(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["app.cli", str(DATA)])
    assert main() == 0
    assert "CASE-002" in capsys.readouterr().out


def test_cli_reports_na_metrics(tmp_path: Path, capsys):
    cases = json.loads(DATA.read_text())
    cases[0]["expected_document_ids"] = []
    cases[0]["required_facts"] = []
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(cases))
    assert main([str(path)]) == 0
    output = capsys.readouterr().out
    assert "coverage=N/A" in output
    assert "facts=N/A" in output


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("{not json", "JSONDecodeError"),
        (json.dumps([{"case_id": "X"}]), "KeyError"),
        (json.dumps({"case_id": "X"}), "TypeError"),
    ],
)
def test_cli_reports_malformed_input_without_traceback(tmp_path: Path, capsys, content, message):
    path = tmp_path / "bad.json"
    path.write_text(content)
    assert main([str(path)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert message in captured.err
    assert "Traceback" not in captured.err


def test_cli_reports_duplicate_document_ids(tmp_path: Path, capsys):
    cases = json.loads(DATA.read_text())
    cases[0]["documents"].append(cases[0]["documents"][0])
    path = tmp_path / "dup.json"
    path.write_text(json.dumps(cases))
    assert main([str(path)]) == 2
    assert "Duplicate document ids" in capsys.readouterr().err


def test_cli_reports_missing_file(tmp_path: Path, capsys):
    assert main([str(tmp_path / "missing.json")]) == 2
    assert "cannot read" in capsys.readouterr().err
