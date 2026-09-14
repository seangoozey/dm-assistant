"""Free arms of the TKT-0104 comparison against the draft v3-live judgments:
lexical baseline and the v5 canonical graph walker (roster edges included).
No provider calls; the native Cognee arm is the paid follow-up."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(r"E:\dm-assistant")
sys.path.insert(0, str(ROOT / "campaign-core/src"))

from dm_assistant_core.application.graph_pilot import GraphPilotRetrieval
from dm_assistant_core.domain.derived_retrieval import evaluate_suggestions
from dm_assistant_core.domain.retrieval import RetrievalQuery, RetrievalRecord

corpus = json.loads((ROOT / ".local/cognee-evaluation/relevance-v3-live-corpus.json").read_text(encoding="utf-8"))
records_by_id = {record["id"]: record for record in corpus["records"]}

records = tuple(RetrievalRecord(
    record_id=record["id"], kind="claim", assertion=record["text"],
    state="established", authority="explicit_lore", visibility="dm_only",
    source_id=f"source-{record['id']}", citation=f"fixture/{record['id']}",
    accepted=True, entity_id=None,
) for record in corpus["records"])


def rank_map(evidence):
    return {item.record_id: position for position, item in enumerate(evidence, start=1)}


def evaluate(arm_name, answer_for):
    satisfied = 0
    for case in corpus["cases"]:
        question = case["question"]
        result = answer_for(question)
        evidence = [item for item in result.evidence]
        ranks = rank_map(evidence)
        pref_rank = ranks.get(case["preferred"])
        over_rank = ranks.get(case["over"])
        missing = [r for r in case.get("required", []) if r not in ranks]
        ok = (pref_rank is not None and (over_rank is None or pref_rank < over_rank)
              and not missing)
        satisfied += ok
        print(f"  {case['id']:22s} {'PASS' if ok else 'FAIL'}  "
              f"preferred rank {pref_rank} vs over {over_rank}"
              + (f"  missing required: {missing}" if missing else "")
              + ("" if pref_rank is not None else "  preferred absent"))
    print(f"{arm_name}: {satisfied}/{len(corpus['cases'])} draft judgments satisfied")
    return satisfied


def lexical(question):
    query = RetrievalQuery(question=question, requester_visibility={"role": "dm"})
    return evaluate_suggestions(query, (), records)

def walker(question):
    query = RetrievalQuery(question=question, requester_visibility={"role": "dm"})
    return pilot.query(query)

# Lexical baseline first.
print("LEXICAL BASELINE")
evaluate("lexical", lexical)

# Canonical walker over bundle v5 (records mocked to the corpus slice; the
# graph structure comes from the real v5 bundle).
bundle = json.loads((ROOT / ".local/cognee-evaluation/live-pilot-v5/bundle.json").read_text(encoding="utf-8"))
bundle_records = {r["record_id"]: r for r in bundle["records"]}
corpus_bundle_records = []
for record in corpus["records"]:
    matching = [r for r in bundle["records"] if r["assertion"] == record["text"]]
    corpus_bundle_records.extend(matching)
pilot_records = []
for raw in corpus_bundle_records:
    pilot_records.append(RetrievalRecord(**{k: v for k, v in raw.items() if k in RetrievalRecord.model_fields}))

repository = MagicMock()
repository.current_records.return_value = tuple(pilot_records)
fallback = MagicMock()
fallback.query.side_effect = lambda q: lexical(q.question)
pilot = GraphPilotRetrieval(fallback, repository,
                            str(ROOT / ".local/cognee-evaluation/live-pilot-v5/bundle.json"))
print()
print("CANONICAL WALKER (bundle v5, roster edges)")
evaluate("walker-v5", walker)
