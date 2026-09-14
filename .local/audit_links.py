"""Read-only audit: which entity->document borrows survive the new matcher rule.

Compares the old rule (any distinctive token overlap) against the new rule
(exact stem, or every distinctive filename token belongs to the entity's name).
Lists borrows the old rule made that the new rule drops — those are the
presentation links that were suspect.
"""
from collections import defaultdict

CONNECTORS = {"the", "of", "and", "for", "history", "myth", "lore", "legend"}


def tokens(value: str) -> list[str]:
    cleaned = "".join(ch if ch.isalnum() else " " for ch in value.lower().replace("'", ""))
    return [t for t in cleaned.split() if t]


def distinctive(parts: list[str]) -> set[str]:
    return {t for t in parts if len(t) > 2 and t not in CONNECTORS}


rows: dict[str, tuple[str, str, set[str]]] = {}
all_names: set[str] = set()
sources: dict[str, set[str]] = defaultdict(set)
with open(".local/entity_doc_links.tsv", encoding="utf-8") as handle:
    for line in handle:
        parts = line.rstrip("\n").split("|")
        if len(parts) != 4:
            continue
        entity_id, name, kind, path = parts
        rows.setdefault(entity_id, (name, kind, set()))
        all_names.add(" ".join(tokens(name)))
        sources[entity_id].add(path)

dropped, kept = [], 0
for entity_id, paths in sources.items():
    name, kind, _ = rows[entity_id]
    normalized = " ".join(tokens(name))
    name_tokens = distinctive(tokens(name))
    for path in sorted(paths):
        stem = path.lower().split("/")[-1].removesuffix(".md")
        stem_parts = [t for t in stem.replace("-", " ").split()]
        stem_distinct = distinctive(stem_parts)
        overlap = stem_distinct & name_tokens
        old_borrows = bool(overlap)
        stem_norm = " ".join(tokens(stem.replace("-", " ")))
        exact = stem_norm == normalized
        clash = stem_norm in all_names and stem_norm != normalized
        new_borrows = exact or (not clash and stem_distinct and stem_distinct <= name_tokens)
        if old_borrows and not new_borrows:
            dropped.append((name, kind, path, sorted(overlap)))
        elif old_borrows:
            kept += 1

print(f"entities with evidence docs: {len(sources)}; borrows kept by new rule: {kept}; borrows dropped: {len(dropped)}")
print("\nDROPPED borrows (old rule showed these documents as the entity's page):")
for name, kind, path, overlap in sorted(dropped):
    print(f"  [{kind:14s}] {name:28s} <- {path}  (shared: {', '.join(overlap)})")
