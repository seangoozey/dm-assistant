"""Offline coverage/discovery check. No provider calls or canonical writes."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "campaign-core/src"))
from dm_assistant_core.application.graph_pilot import graph_targets, normalized


def audit(bundle):
    nodes = dict(bundle["graph"][0])
    covered = {n.get("document_id") for n in nodes.values()
               if n.get("type") == "DocumentChunk" and n.get("text")
               and n.get("text") in bundle["documents"].get(n.get("document_id"), {}).get("text", "")}
    missing = sorted(set(bundle["documents"]) - covered)
    discoveries = {}
    for query in ("Ishi'go'dan", "Tsunadis", "Ragga'na'ken"):
        targets = graph_targets(bundle, query)
        discoveries[query] = [r["citation"] for r in bundle["records"]
                              if r["record_id"] in targets
                              and normalized(query) not in normalized(r["assertion"])]
    return {"records": len(bundle["records"]), "nodes": len(nodes),
            "edges": len(bundle["graph"][1]), "missing_documents": missing,
            "nonlexical_discoveries": discoveries,
            "passed": not missing and any(discoveries.values())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", choices=["live-pilot-v2", "live-pilot-v3"], required=True)
    args = parser.parse_args()
    path = ROOT / ".local/cognee-evaluation" / args.generation
    report = audit(json.loads((path / "bundle.json").read_text(encoding="utf-8")))
    (path / "coverage-audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
    raise SystemExit(0 if report["passed"] else 1)
