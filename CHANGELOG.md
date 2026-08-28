# Changelog

All notable changes to this portfolio project are documented in this file.

The project follows semantic versioning for public portfolio releases. Version numbers describe the repository's software baseline; they do not indicate regulatory or production certification of the evaluation methodology.

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
- No retrieval diagnostics, prompt/model versioning, privacy controls, or monitoring
- Synthetic data only; scores support triage and must not replace qualified human review
