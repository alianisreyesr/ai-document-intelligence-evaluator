import json
from pathlib import Path

import pytest

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
    relaxed = Thresholds(citation_validity=0.5, evidence_coverage=0.5, retrieval_recall_at_k=0.5, groundedness=0.5, required_fact_recall=0.5)
    result = score_case(CASES[1], relaxed)
    assert result["passed"] is True


def test_ranked_retrieval_metrics_measure_recall_and_first_hit():
    case = {
        **CASES[0],
        "candidate": {
            **CASES[0]["candidate"],
            "retrieved_document_ids": ["DOC-NOISE", "DOC-RET-02"],
        },
    }
    result = score_case(case, Thresholds(retrieval_recall_at_k=0.5))
    assert result["metrics"]["retrieval_recall_at_k"] == 0.5
    assert result["metrics"]["retrieval_mrr"] == 0.5


def test_undefined_metrics_are_none_and_not_failures():
    case = {
        **CASES[0],
        "expected_document_ids": [],
        "required_facts": [],
    }
    result = score_case(case)
    for name in ("evidence_coverage", "retrieval_recall_at_k", "required_fact_recall"):
        assert result["metrics"][name] is None
        assert name not in result["failures"]


def _ranked_case(k=None):
    case = {
        **CASES[0],
        "expected_document_ids": ["DOC-A", "DOC-B"],
        "candidate": {**CASES[0]["candidate"], "retrieved_document_ids": ["DOC-X", "DOC-A", "DOC-B"]},
    }
    if k is not None:
        case["k"] = k
    return case


def test_recall_at_k_only_counts_the_top_k_results():
    assert score_case(_ranked_case())["metrics"]["retrieval_recall_at_k"] == 1.0
    assert score_case(_ranked_case(), k=1)["metrics"]["retrieval_recall_at_k"] == 0.0
    assert score_case(_ranked_case(), k=2)["metrics"]["retrieval_recall_at_k"] == 0.5
    assert score_case(_ranked_case(), k=10)["metrics"]["retrieval_recall_at_k"] == 1.0


def test_k_can_come_from_the_case_and_argument_wins():
    assert score_case(_ranked_case(k=2))["metrics"]["retrieval_recall_at_k"] == 0.5
    assert score_case(_ranked_case(k=2), k=3)["metrics"]["retrieval_recall_at_k"] == 1.0


def test_invalid_k_is_rejected():
    for bad in (0, -1, True):
        with pytest.raises(ValueError, match="positive integer"):
            score_case(_ranked_case(), k=bad)


def test_duplicate_document_ids_raise():
    case = {**CASES[0], "documents": [*CASES[0]["documents"], CASES[0]["documents"][0]]}
    with pytest.raises(ValueError, match="Duplicate document ids"):
        score_case(case)
