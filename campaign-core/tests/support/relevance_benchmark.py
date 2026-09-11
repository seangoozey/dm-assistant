"""Offline judged-pool lexical baseline. Never provider/extractor input."""
import json
import re
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[3] / "tests/fixtures/relationship_relevance_cases.json"
FIXTURE_V2 = FIXTURE.with_name("relationship_relevance_cases_v2.json")


def evaluate(corpus, rankings, indexed_ids, *, arm="lexical-token-overlap"):
    rows = []
    for case in corpus["cases"]:
        ranked = rankings.get(case["id"], [])
        if len(ranked) != len(set(ranked)):
            raise ValueError("duplicate results")
        relevant = set(case["required"])
        top = ranked[:10]
        hits = len(relevant & set(top))
        positions = {identity: index for index, identity in enumerate(ranked)}
        rows.append({"id": case["id"], "split": case["split"], "ranked": ranked,
                     "coverage_missing": sorted(relevant - set(indexed_ids)),
                     "pair_correct": case["preferred"] in positions and (
                         case["over"] not in positions or positions[case["preferred"]] < positions[case["over"]]),
                     "recall_at_10": hits / len(relevant),
                     "precision_at_10": hits / len(top) if top else 0})
    return {"version": corpus["version"], "arm": arm,
            "limitations": "Small judged-pool diagnostic; not live retrieval or production acceptance.", "cases": rows}


def baseline():
    corpus = json.loads(FIXTURE.read_text(encoding="utf-8"))
    terms = lambda value: set(re.findall(r"[a-z]{3,}", value.lower()))
    rankings = {}
    for case in corpus["cases"]:
        scored = [(len(terms(case["question"]) & terms(r["text"])), r["id"]) for r in corpus["records"]]
        rankings[case["id"]] = [identity for value, identity in sorted(scored, key=lambda x: (-x[0], x[1])) if value]
    return evaluate(corpus, rankings, [r["id"] for r in corpus["records"]])


def evaluate_v2(corpus, rankings, indexed_ids, returned_paths=None, *, arm="lexical-token-overlap"):
    """Record coverage, explicit-bridge coverage and returned-path coverage stay separate.

    Indexed passage coverage (a record exists in the index) never implies supported
    path coverage (an explicit bridge record connects the chain); a returned path is
    a retrieval explanation, never proof of a transitive campaign fact.
    """
    entities = {r["id"]: frozenset(r.get("entities", ())) for r in corpus["records"]}
    indexed = set(indexed_ids)
    rows = []
    for case in corpus["cases"]:
        ranked = rankings.get(case["id"], [])
        if len(ranked) != len(set(ranked)):
            raise ValueError("duplicate results")
        relevant = set(case["required"])
        top = ranked[:10]
        hits = len(relevant & set(top))
        positions = {identity: index for index, identity in enumerate(ranked)}
        chain = list(case.get("required_path", []))
        bridge_missing = [f"{left}|{right}" for left, right in zip(chain, chain[1:])
                          if left not in indexed or right not in indexed
                          or not (entities.get(left, frozenset())
                                  & entities.get(right, frozenset()))]
        paths = [frozenset(p) for p in (returned_paths or {}).get(case["id"], [])]
        forbidden = {tuple(sorted(pair)) for pair in case.get("absent_bridges", [])}
        rows.append({"id": case["id"], "split": case["split"], "ranked": ranked,
                     "coverage_missing": sorted(relevant - indexed),
                     "bridge_coverage_missing": bridge_missing,
                     "path_covered": (any(frozenset(chain) <= p for p in paths)
                                      if chain else None),
                     "false_bridge_claims": sorted(f"{left}|{right}" for left, right in forbidden
                                                   if any(frozenset((left, right)) <= p for p in paths)),
                     "pair_correct": case["preferred"] in positions and (
                         case["over"] not in positions or positions[case["preferred"]] < positions[case["over"]]),
                     "recall_at_10": hits / len(relevant),
                     "precision_at_10": hits / len(top) if top else 0})
    return {"version": corpus["version"], "arm": arm,
            "limitations": "Small judged-pool diagnostic; not live retrieval or production acceptance.",
            "cases": rows}


def fixture_v2_invariants(corpus):
    """Explicit-bridge corpus promises, checked offline: declared chains bridge
    through records sharing an explicit entity, and forbidden pairs share no
    entity and sit in different components of the explicit-bridge graph."""
    entities = {r["id"]: frozenset(r.get("entities", ())) for r in corpus["records"]}
    chains = [(c["id"], list(c.get("required_path", []))) for c in corpus["cases"]]
    parent = {identity: identity for identity in entities}

    def find(identity):
        while parent[identity] != identity:
            parent[identity] = parent[parent[identity]]
            identity = parent[identity]
        return identity

    ids = list(entities)
    for i, left in enumerate(ids):
        for right in ids[i + 1:]:
            if entities[left] & entities[right]:
                parent[find(left)] = find(right)
    forbidden = [(c["id"], tuple(sorted(pair)))
                 for c in corpus["cases"] for pair in c.get("absent_bridges", [])]
    return {"declared_chains": sum(1 for _, chain in chains if chain),
            "declared_chains_bridged": sum(
                1 for _, chain in chains
                if chain and all(entities.get(a, frozenset()) & entities.get(b, frozenset())
                                 for a, b in zip(chain, chain[1:]))),
            "forbidden_pairs": len(forbidden),
            "forbidden_pairs_share_entity": [f"{case}:{left}|{right}" for case, (left, right) in forbidden
                                             if entities.get(left, frozenset()) & entities.get(right, frozenset())],
            "forbidden_pairs_connected": [f"{case}:{left}|{right}" for case, (left, right) in forbidden
                                          if left in entities and right in entities
                                          and find(left) == find(right)]}


def baseline_v2():
    corpus = json.loads(FIXTURE_V2.read_text(encoding="utf-8"))
    terms = lambda value: set(re.findall(r"[a-z]{3,}", value.lower()))
    rankings = {}
    for case in corpus["cases"]:
        scored = [(len(terms(case["question"]) & terms(r["text"])), r["id"]) for r in corpus["records"]]
        rankings[case["id"]] = [identity for value, identity in sorted(scored, key=lambda x: (-x[0], x[1])) if value]
    return evaluate_v2(corpus, rankings, [r["id"] for r in corpus["records"]])


if __name__ == "__main__":
    print(json.dumps(baseline(), indent=2))
    print(json.dumps(baseline_v2(), indent=2))
