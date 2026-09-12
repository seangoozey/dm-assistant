"""Assemble the v3 live evaluation corpus from the exported real slice.

Offline. Entity associations are derived mentions: a canonical entity name
appearing whole-word in a record's assertion text. The identity space is the
campaign's canonical entity table, never invented names. All judgments are
DRAFT pending Sean's confirmation; none have been tuned against.
"""
import json
import re
import subprocess
from pathlib import Path

SLUGS = {
    "bf317128": "descent-scene", "2c8c0da6": "dariferra-link",
    "d1028ef0": "monk-recovery-status", "d92c4e49": "monastery-sanctuary",
    "a7a50046": "arkin-god-of-magic", "e70fee9c": "ishi-bound-status",
    "025873ae": "roccid-grounded-voice", "5017584c": "myrin-structural-supports",
    "1ab79be4": "romulus-shadow-rule", "86ba3e60": "romulus-aberrant-sorcerer",
    "37971020": "homeland-destroyed", "8710d221": "dariferra-psychic-pressure",
    "2aa59aeb": "leylines-tripled", "472e82f8": "romulus-mortal-malygos-power",
    "b4109e12": "grand-inquisitor", "908b0360": "dariferra-role-sense",
    "4ed0ec13": "malygos-permits-charade", "a977edfd": "wants-romulus-stopped",
    "c9efa039": "power-struggle-symptoms", "05de9584": "malygos-knows-not-priest",
    "6a22b36f": "grey-house-destruction", "cac8a5c7": "fleurite-castle-rule",
    "916d117c": "romulus-direct-chosen", "75f78e51": "stop-infinite-twilight",
    "e2d323a8": "dungeon-torture", "9ce84b67": "church-of-malygos-join",
    "61362a53": "far-realm-corruption", "eb2ab057": "collapse-tunnel-contingency",
    "6fcebc5c": "dariferra-warn-architect", "bf44cef5": "tactical-witness",
    "f3032578": "authoritarian-agenda", "55bca8a1": "tower-description",
    "bb9aff31": "chosen-herald", "4630e045": "coreferra-herald",
    "701fcade": "goodman-reanimated", "eef43a78": "goodman-inquisition-link",
    "b8179716": "ruh-death-aftermath", "83a8b549": "coreferra-brother-warning",
    "592f4192": "breaking-of-splint", "0e915bb5": "city-economy",
}

CASES = [
    {"id": "core-complaint", "split": "draft", "question": "Romulus",
     "preferred": "grand-inquisitor", "over": "tower-description",
     "required": ["grand-inquisitor"]},
    {"id": "causality", "split": "draft", "question": "What increased Romulus's power",
     "preferred": "breaking-of-splint", "over": "tower-description",
     "required": ["breaking-of-splint", "leylines-tripled"]},
    {"id": "organization", "split": "draft", "question": "Romulus's organization",
     "preferred": "grand-inquisitor", "over": "tower-description",
     "required": ["grand-inquisitor", "goodman-inquisition-link"]},
    {"id": "plans", "split": "draft", "question": "What is Romulus planning",
     "preferred": "romulus-shadow-rule", "over": "grey-house-destruction",
     "required": ["romulus-shadow-rule"]},
    {"id": "layout-counterexample", "split": "draft", "question": "Describe the Ishi'ra'la tower",
     "preferred": "tower-description", "over": "breaking-of-splint",
     "required": ["tower-description"]},
    {"id": "monastery", "split": "draft", "question": "Return to the Monastery",
     "preferred": "monastery-sanctuary", "over": "tower-description",
     "required": ["monastery-sanctuary"]},
]


def canonical_entities():
    result = subprocess.run([
        "docker", "exec", "-i", "dm-assistant-campaign-db-1", "psql", "-X", "-t", "-A",
        "-U", "campaign_owner", "-d", "campaign",
        "-c", "BEGIN READ ONLY; SELECT canonical_name FROM entities ORDER BY canonical_name; ROLLBACK;",
    ], capture_output=True, text=True, encoding="utf-8", check=True)
    names = [line.strip() for line in result.stdout.splitlines()
             if line.strip() and line.strip() not in {"BEGIN", "ROLLBACK"}]
    return sorted(names, key=len, reverse=True)


def mentions(text, names):
    found = []
    for name in names:
        pattern = r"(?<![A-Za-z])" + re.escape(name) + r"(?![A-Za-z])"
        if re.search(pattern, text, re.IGNORECASE):
            found.append(name)
    return sorted(found, key=str.lower)


def main():
    root = Path(__file__).resolve().parents[2]
    source = json.loads((root / ".local/cognee-evaluation/relevance-v3-slice-input.json").read_text())
    names = canonical_entities()
    records = []
    for record in source:
        slug = SLUGS.get(record["record_id"][:8])
        if slug is None:
            raise RuntimeError(f"unmapped record {record['record_id']}")
        revision = (record["evidence"][0]["revision_id"] or "")[:8] or "1"
        records.append({"id": slug, "record_id": record["record_id"],
                        "text": record["assertion"], "entities": mentions(record["assertion"], names),
                        "state": record["state"], "authority": record["authority"],
                        "visibility": record["visibility"], "revision": revision})
    corpus = {
        "version": "relative-relevance-v3-live-draft",
        "origin": ("Real canonical claims exported read-only from Campaign PostgreSQL "
                   "(Romulus-neighborhood slice). Entity associations are derived whole-word "
                   "mentions of canonical entity names. ALL judgments are drafts pending "
                   "Sean's confirmation; no held-out split or absent-bridge negatives are "
                   "declared yet. Never committed to the repository."),
        "judgment_status": "draft_pending_sean",
        "records": records, "cases": CASES,
    }
    output = root / ".local/cognee-evaluation/relevance-v3-live-corpus.json"
    output.write_text(json.dumps(corpus, indent=2), encoding="utf-8")
    print(json.dumps({"records": len(records),
                      "cases": len(CASES),
                      "records_without_entity_mentions": [r["id"] for r in records if not r["entities"]],
                      "draft_pairwise": [[c["preferred"], c["over"]] for c in CASES]}))


if __name__ == "__main__":
    main()
