"""Offline traversal + truncation experiment over saved paid-run artifacts.

Reads the saved expanded search report and manifest; no provider calls, no index
writes. Ranking policies compared:
  P0 saved:      manifest-backed tier then co-occurrence, uncapped (as run).
  P1 backed:     manifest-backed records only, capped at 10.
  P2 traversal:  walk-reached records first, then P1 remainder, capped at 10.
Policy choice is made on the development split; held-out is scored once with
whatever policy wins, never re-tuned against its labels.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "campaign-core"))

from manifest_traversal import entity_tokens, manifest_links, walk  # noqa: E402
from tests.support.relevance_benchmark import evaluate_v2  # noqa: E402

RUNTIME = ROOT / ".local" / "cognee-evaluation"


def backed_ranking(join_details, cap=10):
    best, first_seen = {}, {}
    for position, detail in enumerate(join_details):
        if not detail.get("manifest_matched"):
            continue
        for record in detail["records"]:
            first_seen.setdefault(record, position)
            best[record] = max(best.get(record, 0.0), detail["strength"])
    return sorted(best, key=lambda r: (-best[r], first_seen[r]))[:cap]


def cooccurrence_ranking(join_details, cap=10):
    ordered = []
    for detail in join_details:
        if detail.get("manifest_matched"):
            continue
        for record in detail["records"]:
            if record not in ordered:
                ordered.append(record)
    return ordered[:cap]


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--slice", choices=["v2", "live"], default="v2")
    args = parser.parse_args()
    if args.slice == "live":
        corpus_path = RUNTIME / "relevance-v3-live-corpus.json"
        manifest_path = RUNTIME / "relevance-v3-live-manifest.json"
        report_path = RUNTIME / "relevance-v3-live-search-report.json"
        output_path = RUNTIME / "relevance-v3-live-traversal-report.json"
    else:
        corpus_path = ROOT / "tests/fixtures/relationship_relevance_cases_v2.json"
        manifest_path = RUNTIME / "relevance-v2-manifest.json"
        report_path = RUNTIME / "relevance-v2-weighted-search-report.json"
        output_path = RUNTIME / "relevance-v2-traversal-report.json"
    corpus = json.loads(corpus_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    report = json.loads(report_path.read_text())
    links, unresolved, revisions = manifest_links(manifest, corpus)
    tokens = entity_tokens(corpus)
    print(f"links={len(links)} unresolved_edges={len(unresolved)} "
          f"unresolved_records={sorted({r for u in unresolved for r in u['records']})}")

    rankings = {"P0": {}, "P1": {}, "P2": {}}
    paths = {}
    walk_summaries = {}
    for case in corpus["cases"]:
        question = case["question"]
        result = walk(question, links, tokens, revisions)
        walk_records = []
        for w in result["walks"]:
            for record in w["records"]:
                if record not in walk_records:
                    walk_records.append(record)
        details = report["join_details"][case["id"]]
        p1 = backed_ranking(details) or cooccurrence_ranking(details)
        rankings["P0"][case["id"]] = report["rankings"][case["id"]]
        rankings["P1"][case["id"]] = p1
        rankings["P2"][case["id"]] = (walk_records + [r for r in p1 if r not in walk_records])[:10]
        paths[case["id"]] = [w["records"] for w in result["walks"]]
        walk_summaries[case["id"]] = {
            "seeds": result["seeds"], "walks": len(result["walks"]),
            "walk_records": walk_records[:10],
            "chains_covered": any(set(case.get("required_path", [])) <= set(w["records"])
                                  for w in result["walks"]) if case.get("required_path") else None}

    evaluations = {arm: evaluate_v2(corpus, rankings[arm], report["indexed_record_ids"],
                                    returned_paths=paths,
                                    arm=f"cognee-weighted-{arm.lower()}-offline")
                   for arm in rankings}
    artifact = {"links": len(links), "unresolved": unresolved,
                "walks": walk_summaries, "evaluations": evaluations}
    output_path.write_text(json.dumps(artifact, indent=2))

    for arm, ev in evaluations.items():
        dev = [c for c in ev["cases"] if c["split"] == "development"]
        held = [c for c in ev["cases"] if c["split"] == "held_out"]
        print(f"\n{arm}: dev {sum(c['pair_correct'] for c in dev)}/{len(dev)} "
              f"held {sum(c['pair_correct'] for c in held)}/{len(held)} "
              f"false_bridges {sum(len(c['false_bridge_claims']) for c in ev['cases'])}")
        for c in ev["cases"]:
            print(f"  {c['id']:28} {c['split']:12} pair:{str(c['pair_correct']):5} "
                  f"recall:{c['recall_at_10']:.2f} prec:{c['precision_at_10']:.2f} "
                  f"path:{str(c['path_covered']):5}")
    print("\nwalks:", json.dumps(walk_summaries, indent=1))


if __name__ == "__main__":
    main()
