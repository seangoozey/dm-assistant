"""Seed-anchored multi-hop walks over the weighted manifest. Offline; no providers.

Manifest endpoints are resolved to corpus entity tokens: an endpoint joins a walk
only when exactly one declared token matches (equality, or one whole-word set
containing the other). Ambiguous names stay unresolved and their edges are
excluded rather than merged — the Sorin-chain "company" endpoint is ambiguous
with "Ossler's company" by design, and resolving it would fabricate a bridge.
Walks are retrieval explanations over suggested-class links, never transitive
facts; every step keeps its own evidence records and dimensions.
"""
from evidence_paths import Evidence, Link, discover
from weighted_manifest import normalize_name


def entity_tokens(corpus):
    return {normalize_name(token) for record in corpus["records"]
            for token in record.get("entities", ())}


def resolve(tokens, name):
    """Unique matching token for a name, or None when absent/ambiguous."""
    words = set(normalize_name(name).split())
    matches = set()
    for token in tokens:
        token_words = set(token.split())
        if token == name or token_words <= words or words <= token_words:
            matches.add(token)
    return matches.pop() if len(matches) == 1 else None


def manifest_links(manifest, corpus, *, current=True, time_eligible=True):
    """Suggested-class links between resolved endpoints; negated and
    identity-ambiguous edges are reported, not traversed."""
    tokens = entity_tokens(corpus)
    links, unresolved, revisions = [], [], {}
    for position, entry in enumerate(manifest["entries"]):
        for contribution in entry["contributions"]:
            revisions.setdefault(contribution["evidence_id"], contribution["revision"])
        if entry["negated"]:
            continue
        source, target = resolve(tokens, entry["source"]), resolve(tokens, entry["target"])
        if source is None or target is None or source == target:
            unresolved.append({"source": entry["source"], "target": entry["target"],
                               "records": sorted({c["evidence_id"]
                                                  for c in entry["contributions"]})})
            continue
        links.append(Link(
            id=f"manifest-{position}", source=source, target=target,
            relation=entry["relation"], kind="suggested",
            evidence=tuple(Evidence(
                id=contribution["evidence_id"], revision=contribution["revision"],
                state=entry["state"], authority=entry["authority"],
                visibility=entry["visibility"], current=current,
                time_eligible=time_eligible)
                for contribution in entry["contributions"]),
            identities_resolved=True))
    return links, unresolved, revisions


def seed_entities(question, tokens, *, minimum_length=4):
    normalized = normalize_name(question)
    return sorted(token for token in tokens
                  if len(token.replace(" ", "")) >= minimum_length and token in normalized)


def walk(question, links, tokens, revisions, *, allowed_visibility=frozenset({"dm_only"}),
         max_depth=3, fanout=12, budget=100):
    """Bounded walks from question-seeded entities; each walk's records are the
    union of its steps' evidence, in first-contact order."""
    walks = []
    truncated = False
    for seed in seed_entities(question, tokens):
        result = discover(seed, links, allowed_visibility=set(allowed_visibility),
                          current_revisions=revisions, max_depth=max_depth,
                          fanout=fanout, budget=budget)
        truncated |= result["truncated"]
        for path in result["paths"]:
            records: list[str] = []
            for step in path["steps"]:
                for evidence in step["evidence"]:
                    if evidence["id"] not in records:
                        records.append(evidence["id"])
            walks.append({"seed": seed, "target": path["target"], "records": records,
                          "steps": path["steps"]})
    return {"seeds": seed_entities(question, tokens), "walks": walks,
            "truncated": truncated, "meaning": "retrieval_path_not_transitive_fact"}
