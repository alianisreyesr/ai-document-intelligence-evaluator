"""Evaluate a JSON collection of synthetic cases."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.evaluator import score_case


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/evaluation_cases.json")
    cases = json.loads(path.read_text(encoding="utf-8"))
    for case in cases:
        result = score_case(case)
        metrics = result["metrics"]
        print(
            f"{result['case_id']} {'PASS' if result['passed'] else 'FAIL'} "
            f"citation_validity={metrics['citation_validity']:.2f} "
            f"coverage={metrics['evidence_coverage']:.2f} groundedness={metrics['groundedness']:.2f} "
            f"facts={metrics['required_fact_recall']:.2f} latency_ms={metrics['latency_ms']} "
            f"cost_usd={metrics['cost_usd']:.4f}"
        )


if __name__ == "__main__":
    main()
