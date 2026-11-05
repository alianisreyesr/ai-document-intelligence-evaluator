# Changelog

All notable changes to this portfolio project are documented in this file.

The project follows semantic versioning for public portfolio releases. Version numbers describe the repository's software baseline; they do not indicate regulatory or production certification of the evaluation methodology.

## [Unreleased]

### Added

- Optional `k` cut-off for `retrieval_recall_at_k` (API field, case field or `score_case(k=...)`)
- Tests for `app/cli.py` (previously 0% covered), HTML escaping and the new validation
- `ruff` and `mypy` configuration; CI now runs both, tests on Python 3.11 and 3.12 and enforces a 90% coverage threshold

### Changed

- Duplicate document ids now fail with HTTP 422 (API) or exit code 2 (CLI) instead of silently overwriting each other
- `python -m app.cli` reports unreadable or malformed input as an error message instead of a traceback
- `render_dashboard` HTML-escapes case ids and failure names
- Fixed all ruff findings; CI workflow declares minimal `contents: read` permissions; `.gitignore` covers coverage and tooling artifacts

## [1.1.0] — 2026-11-05

### Added

- Retrieval diagnostics: ranked `retrieval_recall_at_k` and `retrieval_mrr` metrics
- Prompt/model versioning: `provider`, `model_version`, `prompt_version` and `retriever_version` metadata with deterministic evaluation IDs
- `GET /api/evaluations/history` (bounded in-process history) and `GET /api/experiments/compare` (pass rate per provider/model)
- Per-request threshold overrides on `POST /api/evaluations`, validated to sane ranges
- Request size limits (list lengths, text length, 1 MB body)
- Non-root Docker image with healthcheck and `.dockerignore`

### Changed

- API version reported by FastAPI is now aligned with the changelog (1.1.0)
- `pytest` and `httpx` moved from `requirements.txt` to `requirements-dev.txt`
- Metrics that are undefined for a case (no expected documents / no required facts) are now `null` (N/A) instead of a vacuous 1.0, and are excluded from averages and failures

### Known limitations

- History and experiment comparison live in process memory: they reset on restart and are per worker
- No authentication on the API

## [1.0.0] — 2026-08-27

### Added

- Deterministic, explainable evaluation harness for document-question answering
- Citation validity, evidence coverage, groundedness proxy, required-fact recall, latency, and estimated-cost scoring
- Provider-neutral candidate-answer adapter and request/response contracts
- FastAPI evaluation API (`/health`, `/api/evaluations`, `/api/thresholds`)
- Python/Streamlit interactive quality dashboard
- Self-contained HTML/JSON evaluation report generator (`app.report`)
- Synthetic golden evaluation dataset and CLI runner (`app.cli`)
- Regression test suite (`pytest`)

### Known limitations

- Lexical overlap is a transparent baseline, not semantic entailment
- No model-based graders, calibration, adversarial datasets, or bias/safety testing
- No retrieval diagnostics, prompt/model versioning, privacy controls, or monitoring (retrieval diagnostics and versioning were added in 1.1.0)
- Synthetic data only; scores support triage and must not replace qualified human review
