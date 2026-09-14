"""Evaluation API and synthetic evidence dashboard."""

import json
import hashlib
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.evaluator import Thresholds, score_case
from app import history
from app.report import evaluate_batch, render_dashboard


app = FastAPI(title="AI Document Intelligence Evaluator", version="0.1.0")
DEMO_CASES = json.loads((Path(__file__).parents[1] / "data" / "evaluation_cases.json").read_text(encoding="utf-8"))


class Document(BaseModel):
    id: str
    text: str = Field(min_length=1)


class Candidate(BaseModel):
    answer: str = Field(min_length=1)
    citations: list[str]
    retrieved_document_ids: Optional[list[str]] = None
    latency_ms: int = Field(ge=0)
    cost_usd: float = Field(ge=0)


class ThresholdOverrides(BaseModel):
    """Per-field overrides for Thresholds; unset fields keep the default."""

    citation_validity: Optional[float] = None
    evidence_coverage: Optional[float] = None
    retrieval_recall_at_k: Optional[float] = None
    retrieval_mrr: Optional[float] = None
    groundedness: Optional[float] = None
    required_fact_recall: Optional[float] = None
    latency_ms: Optional[int] = None
    cost_usd: Optional[float] = None


class EvaluationRequest(BaseModel):
    case_id: str
    documents: list[Document]
    expected_document_ids: list[str]
    required_facts: list[str]
    candidate: Candidate
    thresholds: Optional[ThresholdOverrides] = None
    provider: str = Field(default="unspecified", min_length=1, max_length=80)
    model_version: str = Field(default="unspecified", min_length=1, max_length=120)
    prompt_version: str = Field(default="unspecified", min_length=1, max_length=120)
    retriever_version: str = Field(default="unspecified", min_length=1, max_length=120)




def _evaluation_id(payload: EvaluationRequest) -> str:
    canonical = json.dumps(payload.model_dump(), sort_keys=True, separators=(",", ":"))
    return "EVAL-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12].upper()


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return render_dashboard(evaluate_batch(DEMO_CASES))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "ai_boundary": "evaluation support; human review required"}


@app.get("/api/thresholds")
def thresholds() -> dict[str, float | int]:
    return Thresholds().__dict__


@app.post("/api/evaluations")
def evaluate(payload: EvaluationRequest) -> dict[str, Any]:
    # GET /api/thresholds advertises these as configurable, but this
    # endpoint always scored against Thresholds() and had no field to
    # accept an override — a real capability gap versus that framing.
    limits = Thresholds()
    if payload.thresholds is not None:
        overrides = {
            field: value
            for field, value in payload.thresholds.model_dump().items()
            if value is not None
        }
        limits = replace(limits, **overrides)
    case = payload.model_dump(
        exclude={"thresholds", "provider", "model_version", "prompt_version", "retriever_version"}
    )
    result = score_case(case, limits)
    record = {
        "evaluation_id": _evaluation_id(payload),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "provider": payload.provider,
        "model_version": payload.model_version,
        "prompt_version": payload.prompt_version,
        "retriever_version": payload.retriever_version,
        **result,
    }
    record["thresholds"] = limits.__dict__
    evidence = {key: case[key] for key in ("case_id", "documents", "expected_document_ids", "required_facts")}
    record["evidence_hash"] = hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()
    return history.save(record)


@app.get("/api/evaluations/history")
def evaluation_history(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                       provider: str | None = None, model_version: str | None = None,
                       prompt_version: str | None = None, retriever_version: str | None = None) -> dict[str, Any]:
    filters = dict(provider=provider, model_version=model_version, prompt_version=prompt_version, retriever_version=retriever_version)
    rows = [r for r in history.records() if all(value is None or r[key] == value for key, value in filters.items())]
    return {"count": len(rows[offset:offset+limit]), "total": len(rows), "records": rows[offset:offset+limit], "storage": "sqlite"}


@app.get("/api/evaluations/runs/{run_id}")
def evaluation_run(run_id: str):
    record = history.get(run_id)
    if record is None:
        raise HTTPException(404, "Run not found")
    return record


@app.get("/api/experiments/regressions")
def regressions(baseline: str, candidate: str):
    before, after = history.get(baseline), history.get(candidate)
    if before is None or after is None:
        raise HTTPException(404, "Run not found")
    if before["evidence_hash"] != after["evidence_hash"] or before["thresholds"] != after["thresholds"]:
        raise HTTPException(422, "Comparison requires identical evidence and thresholds")
    deltas = {key: round(after["metrics"][key] - value, 6) for key, value in before["metrics"].items()}
    worse = [key for key, delta in deltas.items() if (delta > 0 if key in ("cost_usd", "latency_ms") else delta < 0)]
    return {"baseline": baseline, "candidate": candidate, "deltas": deltas, "regressions": worse,
            "has_regression": bool(worse), "boundary": "Pairwise observed changes, not statistical significance"}


@app.get("/api/experiments/compare")
def compare_experiments() -> dict[str, Any]:
    records = history.records()
    groups: dict[str, dict[str, Any]] = {}
    for record in records:
        key = f"{record['provider']}::{record['model_version']}"
        group = groups.setdefault(key, {"provider": record["provider"], "model_version": record["model_version"], "runs": 0, "passed": 0})
        group["runs"] += 1
        group["passed"] += int(record["passed"])
    comparisons = [
        {**group, "pass_rate": round(group["passed"] / group["runs"], 4)}
        for group in groups.values()
    ]
    return {"count": len(comparisons), "models": sorted(comparisons, key=lambda item: (-item["pass_rate"], item["provider"], item["model_version"]))}
