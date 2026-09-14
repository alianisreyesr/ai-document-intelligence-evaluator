import pytest


@pytest.fixture(autouse=True)
def isolated_history(tmp_path, monkeypatch):
    monkeypatch.setenv("EVALUATION_DB_PATH", str(tmp_path / "evaluations.db"))
