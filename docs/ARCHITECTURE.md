# Architecture

```mermaid
flowchart LR
  A["Synthetic golden cases"] --> D["Deterministic evaluator"]
  B["Candidate answer"] --> D
  C["Retrieved evidence"] --> D
  D --> E["Per-case metric record"]
  E --> F["Threshold decision"]
  F -->|pass| G["Human acceptance review"]
  F -->|fail| H["Failure diagnostics"]
  E --> I["Streamlit dashboard"]
  E --> J["HTML and JSON evidence export"]
  K["FastAPI evaluation endpoint"] --> D
```

## Runtime boundaries

The evaluator is provider-neutral and deterministic. The Streamlit dashboard reads the same batch report as the CLI and FastAPI layer; it does not implement a separate scoring path.

```mermaid
sequenceDiagram
  participant Reviewer
  participant Dashboard as Streamlit dashboard
  participant Report as Batch report
  participant Evaluator
  participant Dataset as Synthetic golden set
  Reviewer->>Dashboard: Open evaluation view
  Dashboard->>Report: Request current report
  Report->>Dataset: Load evaluation cases
  loop Each case
    Report->>Evaluator: Score evidence and candidate answer
    Evaluator-->>Report: Metrics, failures, and decision
  end
  Report-->>Dashboard: Summary and case-level evidence
  Dashboard-->>Reviewer: Filters, comparisons, and review queue
```

## Production evolution

```mermaid
flowchart LR
  A["Versioned retrieval pipeline"] --> B["Provider adapters"]
  B --> C["Expanded golden and adversarial sets"]
  C --> D["Deterministic and calibrated semantic graders"]
  D --> E["Experiment comparison"]
  E --> F["Human review workflow"]
  G["Privacy, safety, and monitoring controls"] -. governs .-> A
  G -. governs .-> D
  G -. governs .-> F
```
