"""Phase-1 identity-gap detector (offline proof for TKT-0106). Deterministic.

Read-only against the campaign database plus the saved live-slice traversal
audit. Mines recurring proper-noun phrases in current canonical claims that
match no canonical entity or alias, then ranks them by claim frequency and by
measured retrieval demand (unresolved extracted endpoints). Output is derived
review material only — nothing is created, merged, or written.
"""
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / ".local/cognee-evaluation"

CONNECTORS = {"of", "the", "de", "le", "la", "von", "van"}
NON_NAMES = {
    "the", "a", "an", "he", "she", "it", "they", "we", "his", "her", "its", "their",
    "status", "location", "affiliation", "disposition", "appearance", "personality",
    "background", "abilities", "powers", "relationships", "current", "date", "time",
    "place", "purpose", "description", "event", "consequence", "section", "notes",
    "chapter", "scene", "floor", "tower", "city", "camp", "key", "lessons", "running",
    "early", "life", "pre", "post", "party", "players", "party's", "first", "second",
    "third", "final", "initial", "each", "if", "when", "after", "before", "upon",
    "survived", "created", "destroyed", "ruled", "ruled", "ruling", "born",
}
NAME_WORD = re.compile(r"[A-Z][a-zA-Z'’\-]*[a-z][a-zA-Z'’\-]*|[A-Z]{2,}")
# Connector chains ("Court of the Stars") are allowed between capitalized words.
PHRASE = re.compile(
    r"\b[A-Z][\w'’\-]*(?:(?:\s+(?:of|the|de|le|la|von|van))+\s+[A-Z][\w'’-]*|\s+[A-Z][\w'’-]*){0,3}")


def psql(sql):
    result = subprocess.run([
        "docker", "exec", "-i", "dm-assistant-campaign-db-1", "psql", "-X", "-t", "-A",
        "-U", "campaign_owner", "-d", "campaign", "-v", "ON_ERROR_STOP=1",
        "-c", "BEGIN READ ONLY; " + sql + " ROLLBACK;",
    ], capture_output=True, text=True, encoding="utf-8", check=True)
    body = result.stdout.removeprefix("BEGIN\n").removesuffix("ROLLBACK\n").strip()
    return json.loads(body)


def phrases(text):
    for match in PHRASE.finditer(text):
        candidate = " ".join(match.group(0).split())
        words = candidate.split()
        if all(word.lower() in CONNECTORS or not NAME_WORD.fullmatch(word) for word in words):
            continue
        if candidate.lower() in NON_NAMES:
            continue
        yield candidate


def main():
    claims = psql("""
SELECT coalesce(json_agg(row_to_json(x)), '[]'::json) FROM (
 SELECT c.id, c.assertion_text, c.visibility FROM claims c
 WHERE c.state IN ('established','observed','intended','prepared')
 AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id=c.id)
) x;""")
    entities = psql("""
SELECT coalesce(json_agg(row_to_json(x)), '[]'::json) FROM (
 SELECT e.canonical_name, coalesce((SELECT json_agg(a.alias) FROM entity_aliases a
  WHERE a.entity_id=e.id), '[]'::json) AS aliases FROM entities e
) x;""")
    known = {name.strip().casefold() for entity in entities
             for name in [entity["canonical_name"], *entity["aliases"]] if name}

    # Words that appear frequently in lowercase are sentence-start noise, not names.
    lowercase_common = Counter()
    for claim in claims:
        lowercase_common.update(word for word in re.findall(r"[a-z][\w'’\-]+",
                                     claim["assertion_text"]) if word not in CONNECTORS)

    demand = Counter()
    audit = RUNTIME / "relevance-v3-live-traversal-report.json"
    if audit.exists():
        for edge in json.loads(audit.read_text(encoding="utf-8"))["unresolved"]:
            for endpoint in (edge["source"], edge["target"]):
                demand[endpoint.strip().casefold()] += len(edge["records"])

    claim_counts, mention_counts, examples = Counter(), Counter(), {}
    for claim in claims:
        seen = set()
        for phrase in phrases(claim["assertion_text"]):
            key = phrase.casefold()
            if key in known or key in NON_NAMES:
                continue
            words = [word for word in phrase.split() if word.lower() not in CONNECTORS]
            if words and sum(lowercase_common[word.lower()] > 10 for word in words) == len(words):
                continue
            seen.add(key)
            mention_counts[key] += 1
            examples.setdefault(key, phrase)
        for key in seen:
            claim_counts[key] += 1

    ranked = []
    for key, claims_with in claim_counts.most_common():
        surface = examples[key]
        alias_of = sorted(name for name in known
                          if name in key or key in name) if len(key) > 3 else []
        ranked.append({
            "surface": surface,
            "claims_with_phrase": claims_with,
            "total_mentions": mention_counts[key],
            "retrieval_demand_edges": demand.get(key, 0),
            "alias_candidate_of": alias_of,
            "suggested_decision": "add_alias" if alias_of else "review",
        })
    ranked.sort(key=lambda item: (-item["retrieval_demand_edges"],
                                  -item["claims_with_phrase"], -item["total_mentions"],
                                  item["surface"]))
    output = RUNTIME / "identity-gap-candidates.json"
    output.write_text(json.dumps({"generated_from": "current canonical claims, read-only",
                                  "claims_scanned": len(claims),
                                  "known_identities": len(known),
                                  "candidates": ranked}, indent=2), encoding="utf-8")
    print(f"claims scanned: {len(claims)}; known identities: {len(known)}; "
          f"candidates: {len(ranked)} -> {output.name}")
    for item in ranked[:25]:
        print(f"  demand={item['retrieval_demand_edges']:3}  claims={item['claims_with_phrase']:3}  "
              f"mentions={item['total_mentions']:3}  {item['surface']!r}"
              + (f"  -> alias of {item['alias_candidate_of']}" if item['alias_candidate_of'] else ""))


if __name__ == "__main__":
    main()
