"""Interactive Streamlit dashboard for deterministic AI evaluation evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from app.report import evaluate_batch


ROOT = Path(__file__).parent
DATASET = ROOT / "data" / "evaluation_cases.json"


@st.cache_data
def load_report(dataset_path: str) -> dict[str, object]:
    """Evaluate the synthetic golden set and cache the deterministic report."""
    cases = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    return evaluate_batch(cases)


def result_frame(report: dict[str, object]) -> pd.DataFrame:
    """Flatten evaluation results for interactive review."""
    rows = []
    for result in report["results"]:
        rows.append(
            {
                "case_id": result["case_id"],
                "decision": "Pass" if result["passed"] else "Human review",
                **result["metrics"],
                "failures": ", ".join(result["failures"]) or "None",
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    st.set_page_config(page_title="AI Quality Dashboard", page_icon="🧠", layout="centered")
    st.title("AI Quality Dashboard")
    st.caption("Provider-neutral, deterministic evaluation evidence built from a synthetic golden set.")

    report = load_report(str(DATASET))
    summary = report["summary"]
    averages = report["averages"]
    first_row = st.columns(3)
    first_row[0].metric("Cases", summary["total"])
    first_row[1].metric("Pass rate", f"{summary['pass_rate']:.0%}")
    first_row[2].metric("Citation validity", f"{averages['citation_validity']:.2f}")
    second_row = st.columns(3)
    second_row[0].metric("Groundedness", f"{averages['groundedness']:.2f}")
    second_row[1].metric("Avg. latency", f"{averages['latency_ms']:.0f} ms")
    second_row[2].metric("Avg. cost", f"${averages['cost_usd']:.4f}")

    results = result_frame(report)
    st.subheader("Evaluation dimensions by case")
    selected_metrics = st.multiselect(
        "Metrics",
        ["citation_validity", "evidence_coverage", "groundedness", "required_fact_recall"],
        default=["citation_validity", "evidence_coverage", "groundedness", "required_fact_recall"],
    )
    if selected_metrics:
        st.bar_chart(results.set_index("case_id")[selected_metrics])

    st.subheader("Failure diagnostics")
    failures = pd.DataFrame(
        sorted(report["failure_counts"].items(), key=lambda item: item[1], reverse=True),
        columns=["failure", "count"],
    )
    if failures.empty:
        st.success("No threshold failures")
    else:
        st.dataframe(failures, width="stretch", hide_index=True)

    st.subheader("Golden-set review queue")
    decision = st.segmented_control("Decision", ["All", "Pass", "Human review"], default="All")
    displayed = results if decision == "All" else results[results["decision"] == decision]
    st.dataframe(
        displayed,
        width="stretch",
        hide_index=True,
        column_config={
            "cost_usd": st.column_config.NumberColumn("Cost", format="$%.4f"),
            "latency_ms": st.column_config.NumberColumn("Latency", format="%d ms"),
        },
    )

    with st.expander("Evaluation boundary"):
        st.write(
            "These transparent lexical metrics support regression testing and triage. They do not establish "
            "factual correctness, semantic entailment, safety, or production readiness; human review remains required."
        )


if __name__ == "__main__":
    main()
