"""Evaluation API."""

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.evaluator import Thresholds, score_case


app = FastAPI(title="AI Document Intelligence Evaluator", version="0.1.0")


class Document(BaseModel):
    id: str
    text: str = Field(min_length=1)


class Candidate(BaseModel):
    answer: str = Field(min_length=1)
    citations: list[str]
    latency_ms: int = Field(ge=0)
    cost_usd: float = Field(ge=0)


class EvaluationRequest(BaseModel):
    case_id: str
    documents: list[Document]
    expected_document_ids: list[str]
    required_facts: list[str]
    candidate: Candidate


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "ai_boundary": "evaluation support; human review required"}


@app.get("/api/thresholds")
def thresholds() -> dict[str, float | int]:
    return Thresholds().__dict__


@app.post("/api/evaluations")
def evaluate(payload: EvaluationRequest) -> dict[str, Any]:
    return score_case(payload.model_dump())
