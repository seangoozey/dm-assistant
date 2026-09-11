"""Run with Campaign Core's Python; reads synthetic reports, never calls providers."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "campaign-core"))

from tests.support.connected_knowledge_harness import load, run
from tests.support.knowledge_evaluation import EvaluationRun, score


def main():
    runtime = ROOT / ".local/cognee-evaluation"
    combined = None
    scope_status = {}
    for scope in ("dm", "party", "conflict"):
        path = runtime / f"corpus-{scope}-report.json"
        if not path.exists():
            scope_status[scope] = "not_run"
            continue
        report = json.loads(path.read_text())
        scope_status[scope] = "completed" if report["success"] else report.get("error_type", "query_errors")
        if "evaluation" not in report:
            continue
        if combined is None:
            combined = {**report["evaluation"], "outputs": []}
        combined["outputs"].extend(report["evaluation"]["outputs"])
    if combined is None:
        raise ValueError("no corpus query outputs")
    corpus = load()
    scored = score(corpus, EvaluationRun.model_validate(combined))
    baseline = run(corpus)
    rows = scored["cases"]
    measured = [r for r in rows if not r["failed"] and r["recall_at_10"] is not None]
    compared_ids = {r["case_id"] for r in measured}
    lexical = [r for r in baseline["cases"] if r["id"] in compared_ids]
    summary = {
        "scope_status": scope_status, "queried_cases": len(rows) - scored["failed_cases"],
        "full_recall_cases": sum(r["recall_at_10"] == 1 for r in measured),
        "mean_recall": sum(r["recall_at_10"] for r in measured) / len(measured) if measured else None,
        "mean_precision": sum(r["precision_at_10"] or 0 for r in measured) / len(measured) if measured else None,
        "lexical_mean_recall_same_cases": sum(r["recall_at_10"] for r in lexical) / len(lexical) if lexical else None,
        "lexical_mean_precision_same_cases": sum(r["precision_at_10"] or 0 for r in lexical) / len(lexical) if lexical else None,
        "violations": {r["case_id"]: r["forbidden_evidence_ids"] for r in rows if r["forbidden_evidence_ids"]},
        "incomplete_recall": {r["case_id"]: r["recall_at_10"] for r in measured if r["recall_at_10"] < 1},
        "limitations": "Evidence retrieval only. Modes, semantic paths, support eligibility and entailment unimplemented; do not interpret mode failures as measured answer quality.",
    }
    (runtime / "corpus-scored.json").write_text(json.dumps({"summary": summary, "scored": scored,
                                                        "lexical_baseline": baseline}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
