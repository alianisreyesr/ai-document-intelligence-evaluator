"""Batch evaluation reporting and recruiter-facing dashboard generation."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from app.evaluator import score_case


def evaluate_batch(cases: list[dict]) -> dict[str, object]:
    results = [score_case(case) for case in cases]
    failures = Counter(failure for result in results for failure in result["failures"])
    total = len(results)
    passed = sum(result["passed"] for result in results)
    averages = {
        metric: round(sum(float(result["metrics"][metric]) for result in results) / total, 4) if total else 0
        for metric in ("citation_validity", "evidence_coverage", "groundedness", "required_fact_recall", "latency_ms", "cost_usd")
    }
    return {
        "summary": {"total": total, "passed": passed, "failed": total - passed, "pass_rate": round(passed / total, 4) if total else 0},
        "averages": averages,
        "failure_counts": dict(failures),
        "results": results,
    }


def render_dashboard(report: dict[str, object]) -> str:
    summary = report["summary"]
    averages = report["averages"]
    result_rows = "".join(
        f"<tr><td>{result['case_id']}</td><td><span class='status {'pass' if result['passed'] else 'fail'}'>{'Pass' if result['passed'] else 'Review'}</span></td><td>{result['metrics']['citation_validity']:.2f}</td><td>{result['metrics']['evidence_coverage']:.2f}</td><td>{result['metrics']['groundedness']:.2f}</td><td>{result['metrics']['required_fact_recall']:.2f}</td><td>{result['metrics']['latency_ms']} ms</td><td>${result['metrics']['cost_usd']:.4f}</td></tr>"
        for result in report["results"]
    )
    failure_rows = "".join(
        f"<li><span>{name.replace('_', ' ').title()}</span><strong>{count}</strong></li>" for name, count in report["failure_counts"].items()
    ) or "<li><span>No threshold failures</span><strong>0</strong></li>"
    return f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>AI Evaluation Dashboard</title><style>
:root{{--ink:#172033;--muted:#667085;--line:#e4e7ec;--purple:#6941c6;--green:#067647;--red:#b42318;--bg:#f7f7fb}}*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);font:15px Inter,system-ui;color:var(--ink)}}main{{max-width:1180px;margin:auto;padding:42px 28px}}.eyebrow{{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--purple);font-weight:800}}
h1{{font-size:38px;margin:8px 0}}.sub{{color:var(--muted);max-width:800px}}.metrics{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin:28px 0}}
.card,.panel{{background:#fff;border:1px solid var(--line);border-radius:14px;box-shadow:0 8px 26px #1720330c}}.card{{padding:18px}}.label{{font-size:11px;text-transform:uppercase;color:var(--muted)}}.value{{font-size:26px;font-weight:800;margin-top:7px}}
.layout{{display:grid;grid-template-columns:2.2fr .8fr;gap:18px}}.panel{{padding:22px}}h2{{font-size:18px;margin:0 0 16px}}table{{width:100%;border-collapse:collapse}}th,td{{padding:12px 8px;border-bottom:1px solid var(--line);text-align:left}}th{{font-size:10px;text-transform:uppercase;color:var(--muted)}}
.status{{font-weight:750;padding:5px 9px;border-radius:99px}}.pass{{background:#ecfdf3;color:var(--green)}}.fail{{background:#fef3f2;color:var(--red)}}ul{{list-style:none;padding:0;margin:0}}li{{display:flex;justify-content:space-between;padding:11px 0;border-bottom:1px solid var(--line)}}footer{{color:var(--muted);font-size:12px;margin-top:18px}}@media(max-width:900px){{.metrics{{grid-template-columns:repeat(2,1fr)}}.layout{{grid-template-columns:1fr}}}}
</style></head><body><main><div class='eyebrow'>Provider-neutral evaluation evidence</div><h1>AI Quality Dashboard</h1><p class='sub'>Transparent evidence for citation validity, grounding, required facts, latency, and cost—with failed cases routed to human review.</p>
<section class='metrics'><div class='card'><div class='label'>Cases</div><div class='value'>{summary['total']}</div></div><div class='card'><div class='label'>Pass rate</div><div class='value'>{summary['pass_rate']:.0%}</div></div><div class='card'><div class='label'>Citation validity</div><div class='value'>{averages['citation_validity']:.2f}</div></div><div class='card'><div class='label'>Groundedness</div><div class='value'>{averages['groundedness']:.2f}</div></div><div class='card'><div class='label'>Avg latency</div><div class='value'>{averages['latency_ms']:.0f}ms</div></div><div class='card'><div class='label'>Avg cost</div><div class='value'>${averages['cost_usd']:.4f}</div></div></section>
<section class='layout'><article class='panel'><h2>Golden-set results</h2><table><thead><tr><th>Case</th><th>Decision</th><th>Citations</th><th>Coverage</th><th>Grounding</th><th>Facts</th><th>Latency</th><th>Cost</th></tr></thead><tbody>{result_rows}</tbody></table></article><aside class='panel'><h2>Failure diagnostics</h2><ul>{failure_rows}</ul></aside></section>
<footer>Synthetic evaluation cases · deterministic baseline metrics · human review remains required</footer></main></body></html>"""


def export_report(input_path: Path, output_path: Path) -> dict[str, object]:
    cases = json.loads(input_path.read_text(encoding="utf-8"))
    report = evaluate_batch(cases)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_dashboard(report), encoding="utf-8")
    output_path.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/evaluation_cases.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/evaluation-dashboard.html"))
    args = parser.parse_args()
    report = export_report(args.input, args.output)
    print(f"dashboard={args.output} total={report['summary']['total']} pass_rate={report['summary']['pass_rate']:.0%}")


if __name__ == "__main__":
    main()
