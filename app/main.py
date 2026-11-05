"""Evaluation API and synthetic evidence dashboard."""

import hashlib
import json
import threading
from collections import deque
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, model_validator

from app.evaluator import Thresholds, score_case
from app.report import evaluate_batch, render_dashboard

app = FastAPI(title="AI Document Intelligence Evaluator", version="1.1.0")
DEMO_CASES = json.loads((Path(__file__).parents[1] / "data" / "evaluation_cases.json").read_text(encoding="utf-8"))


# Input size limits (DoS guard). Bodies above MAX_BODY_BYTES get HTTP 413.
MAX_BODY_BYTES = 1_000_000
MAX_ITEMS = 100
MAX_ID_LENGTH = 200
MAX_TEXT_LENGTH = 50_000


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        return JSONResponse({"detail": "Request body too large."}, status_code=413)
    return await call_next(request)


class Document(BaseModel):
    id: str = Field(max_length=MAX_ID_LENGTH)
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)


class Candidate(BaseModel):
    answer: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    citations: list[str] = Field(max_length=MAX_ITEMS)
    retrieved_document_ids: list[str] | None = Field(default=None, max_length=MAX_ITEMS)
    latency_ms: int = Field(ge=0)
    cost_usd: float = Field(ge=0)


class ThresholdOverrides(BaseModel):
    """Per-field overrides for Thresholds; unset fields keep the default."""

    citation_validity: float | None = Field(default=None, ge=0, le=1)
    evidence_coverage: float | None = Field(default=None, ge=0, le=1)
    retrieval_recall_at_k: float | None = Field(default=None, ge=0, le=1)
    retrieval_mrr: float | None = Field(default=None, ge=0, le=1)
    groundedness: float | None = Field(default=None, ge=0, le=1)
    required_fact_recall: float | None = Field(default=None, ge=0, le=1)
    latency_ms: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0, allow_inf_nan=False)


class EvaluationRequest(BaseModel):
    case_id: str = Field(max_length=MAX_ID_LENGTH)
    documents: list[Document] = Field(max_length=MAX_ITEMS)
    expected_document_ids: list[str] = Field(max_length=MAX_ITEMS)
    required_facts: list[str] = Field(max_length=MAX_ITEMS)
    candidate: Candidate
    thresholds: ThresholdOverrides | None = None
    provider: str = Field(default="unspecified", min_length=1, max_length=80)
    model_version: str = Field(default="unspecified", min_length=1, max_length=120)
    prompt_version: str = Field(default="unspecified", min_length=1, max_length=120)
    retriever_version: str = Field(default="unspecified", min_length=1, max_length=120)
    k: int | None = Field(default=None, ge=1, le=MAX_ITEMS, description="Retrieval cut-off for recall@k")

    @model_validator(mode="after")
    def _reject_duplicate_document_ids(self) -> "EvaluationRequest":
        ids = [document.id for document in self.documents]
        duplicates = sorted({document_id for document_id in ids if ids.count(document_id) > 1})
        if duplicates:
            raise ValueError(f"Duplicate document ids: {', '.join(duplicates)}")
        return self


_HISTORY_LIMIT = 500
_history: deque[dict[str, Any]] = deque(maxlen=_HISTORY_LIMIT)
_history_lock = threading.Lock()


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
        exclude={"thresholds", "provider", "model_version", "prompt_version", "retriever_version", "k"}
    )
    result = score_case(case, limits, k=payload.k)
    record = {
        "evaluation_id": _evaluation_id(payload),
        "evaluated_at": datetime.now(UTC).isoformat(),
        "provider": payload.provider,
        "model_version": payload.model_version,
        "prompt_version": payload.prompt_version,
        "retriever_version": payload.retriever_version,
        **result,
    }
    with _history_lock:
        _history.appendleft(record)
    return record


@app.get("/api/evaluations/history")
def evaluation_history(limit: int = 50) -> dict[str, Any]:
    safe_limit = min(max(limit, 1), 100)
    with _history_lock:
        records = list(_history)[:safe_limit]
    return {"count": len(records), "records": records, "storage": "bounded-process-memory"}


@app.get("/api/experiments/compare")
def compare_experiments() -> dict[str, Any]:
    with _history_lock:
        records = list(_history)
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
