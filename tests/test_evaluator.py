import json
from pathlib import Path

from app.evaluator import Thresholds, score_case, tokens


CASES = json.loads((Path(__file__).parents[1] / "data" / "evaluation_cases.json").read_text())


def test_tokenization_removes_common_stop_words():
    assert tokens("The refund is to the original payment method") == {"refund", "original", "payment", "method"}


def test_grounded_candidate_passes():
    result = score_case(CASES[0])
    assert result["passed"] is True
    assert result["failures"] == []
    assert result["metrics"]["citation_validity"] == 1.0
    assert result["metrics"]["required_fact_recall"] == 1.0


def test_unsupported_candidate_has_explainable_failures():
    result = score_case(CASES[1])
    assert result["passed"] is False
    assert "citation_validity" in result["failures"]
    assert "evidence_coverage" in result["failures"]
    assert "required_fact_recall" in result["failures"]


def test_thresholds_are_configurable():
    relaxed = Thresholds(citation_validity=0.5, evidence_coverage=0.5, groundedness=0.5, required_fact_recall=0.5)
    result = score_case(CASES[1], relaxed)
    assert result["passed"] is True
