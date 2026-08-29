"""Evaluation API and synthetic evidence dashboard."""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.evaluator import Thresholds, score_case
from app.report import evaluate_batch, render_dashboard


app = FastAPI(title="AI Document Intelligence Evaluator", version="0.1.0")
DEMO_CASES = json.loads((Path(__file__).parents[1] / "data" / "evaluation_cases.json").read_text(encoding="utf-8"))


class Document(BaseModel):
    id: str
    text: str = Field(min_length=1)


class Candidate(BaseModel):
    answer: str = Field(min_length=1)
    citations: list[str]
    latency_ms: int = Field(ge=0)
    cost_usd: float = Field(ge=0)


class ThresholdOverrides(BaseModel):
    """Per-field overrides for Thresholds; unset fields keep the default."""

    citation_validity: Optional[float] = None
    evidence_coverage: Optional[float] = None
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
    case = payload.model_dump(exclude={"thresholds"})
    return score_case(case, limits)
