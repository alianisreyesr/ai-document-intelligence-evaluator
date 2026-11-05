"""Evaluate a JSON collection of synthetic cases."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.evaluator import score_case


def _fmt(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    path = Path(args[0]) if args else Path("data/evaluation_cases.json")
    try:
        cases = json.loads(path.read_text(encoding="utf-8"))
        results = [score_case(case) for case in cases]
    except OSError as exc:
        print(f"error: cannot read {path}: {exc.strerror or exc}", file=sys.stderr)
        return 2
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"error: invalid evaluation cases in {path}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    for result in results:
        metrics = result["metrics"]
        print(
            f"{result['case_id']} {'PASS' if result['passed'] else 'FAIL'} "
            f"citation_validity={metrics['citation_validity']:.2f} "
            f"coverage={_fmt(metrics['evidence_coverage'])} groundedness={metrics['groundedness']:.2f} "
            f"facts={_fmt(metrics['required_fact_recall'])} latency_ms={metrics['latency_ms']} "
            f"cost_usd={metrics['cost_usd']:.4f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
