# Case study: evaluating document-grounded AI answers

## Problem

Fluent answers can contain invalid citations, omit required evidence, introduce unsupported claims, or exceed operational cost and latency targets. A chatbot screenshot does not expose those risks.

## Evaluation response

This project treats evaluation as a repeatable software workflow. Each synthetic golden case contains available documents, expected evidence identifiers, required facts, and a candidate answer with citations and operational telemetry.

## Decisions

- Metrics are deterministic and inspectable before introducing model-based graders.
- Citation existence and evidence coverage are separate measurements.
- The groundedness baseline uses only validly cited context.
- Latency and cost are evaluated alongside answer quality.
- Threshold failures route a result to analysis and human review.

## Limitations

Lexical groundedness cannot detect every contradiction or valid paraphrase. Production evaluation requires calibrated semantic graders, diverse expert-reviewed datasets, retrieval metrics, red-team cases, subgroup analysis, privacy controls, and continuous monitoring.

## Verified result

The synthetic golden set contains one passing case and one intentionally failing case. Ten automated tests verify metric behavior, configurable thresholds, API boundaries, interactive Streamlit rendering, batch aggregation, failure diagnostics, and HTML/JSON export. The demonstration report produces a 50% pass rate so reviewers can inspect both success and failure evidence.
