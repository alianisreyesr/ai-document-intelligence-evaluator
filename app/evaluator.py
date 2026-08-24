"""Deterministic evaluation metrics for document-grounded answers."""

from __future__ import annotations

import re
from dataclasses import dataclass


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
STOP_WORDS = {"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it", "of", "on", "or", "that", "the", "to", "was", "with"}


def tokens(text: str) -> set[str]:
    return {token for token in TOKEN_PATTERN.findall(text.lower()) if token not in STOP_WORDS and len(token) > 1}


@dataclass(frozen=True)
class Thresholds:
    citation_validity: float = 1.0
    evidence_coverage: float = 0.8
    groundedness: float = 0.7
    required_fact_recall: float = 0.8
    latency_ms: int = 1500
    cost_usd: float = 0.01


def score_case(case: dict, thresholds: Thresholds | None = None) -> dict[str, object]:
    limits = thresholds or Thresholds()
    documents = {document["id"]: document["text"] for document in case["documents"]}
    cited = set(case["candidate"]["citations"])
    valid_citations = cited & documents.keys()
    expected = set(case["expected_document_ids"])

    citation_validity = len(valid_citations) / len(cited) if cited else 0.0
    evidence_coverage = len(valid_citations & expected) / len(expected) if expected else 1.0

    answer_tokens = tokens(case["candidate"]["answer"])
    context_tokens = tokens(" ".join(documents[document_id] for document_id in valid_citations))
    groundedness = len(answer_tokens & context_tokens) / len(answer_tokens) if answer_tokens else 0.0

    answer_lower = case["candidate"]["answer"].lower()
    required_facts = case["required_facts"]
    required_fact_recall = sum(fact.lower() in answer_lower for fact in required_facts) / len(required_facts) if required_facts else 1.0

    latency_ms = int(case["candidate"]["latency_ms"])
    cost_usd = float(case["candidate"]["cost_usd"])
    metrics = {
        "citation_validity": round(citation_validity, 4),
        "evidence_coverage": round(evidence_coverage, 4),
        "groundedness": round(groundedness, 4),
        "required_fact_recall": round(required_fact_recall, 4),
        "latency_ms": latency_ms,
        "cost_usd": cost_usd,
    }
    failures = [
        name
        for name, passed in {
            "citation_validity": citation_validity >= limits.citation_validity,
            "evidence_coverage": evidence_coverage >= limits.evidence_coverage,
            "groundedness": groundedness >= limits.groundedness,
            "required_fact_recall": required_fact_recall >= limits.required_fact_recall,
            "latency_ms": latency_ms <= limits.latency_ms,
            "cost_usd": cost_usd <= limits.cost_usd,
        }.items()
        if not passed
    ]
    return {"case_id": case["case_id"], "passed": not failures, "failures": failures, "metrics": metrics}
