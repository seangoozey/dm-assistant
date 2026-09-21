"""Scan session-note contents for in-world date references (read-only)."""
import re
import subprocess

SEP = "@@ROWSEP@@"
sql = f"""
SELECT sdp.normalized_path || '{SEP}' || encode(sr.raw_content, 'escape')
FROM source_documents sd
JOIN source_document_paths sdp ON sdp.source_document_id = sd.id
JOIN LATERAL (SELECT raw_content FROM source_revisions WHERE source_document_id = sd.id
              ORDER BY captured_at DESC LIMIT 1) sr ON true
WHERE sdp.normalized_path LIKE 'sessions/%'
ORDER BY sdp.normalized_path;
"""
result = subprocess.run(
    ["docker", "exec", "-i", "dm-assistant-campaign-db-1", "psql", "-X", "-t", "-A",
     "-U", "campaign_owner", "-d", "campaign", "-c", sql],
    capture_output=True, text=True, encoding="utf-8", check=True)

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
PATTERNS = [
    (r"\b\d{1,2}/\d{1,2}/\d{2,3}\b", "d/m/yy"),
    (r"\b\d{3}\s*CE\b|\b\d{3}\s*c\.?e\.?\b", "CE year"),
    (r"\b\d{3}-\d{1,2}-\d{1,2}\b", "year-m-d"),
    (rf"\b\d{{1,2}}(st|nd|rd|th)?\s+(of\s+)?({MONTHS})\b", "day Month"),
    (rf"\b({MONTHS})\s+\d{{1,2}}(st|nd|rd|th)?\b", "Month day"),
    (r"\byear\s+of\s+\d{3}\b|\bYear\s+\d{3}\b|\byear\s+\d{3}\b", "year N"),
    (r"\b[1-9]\d?\s+(days?|weeks?|months?)\s+(later|after|ago|pass)\b", "relative"),
]

rows = [chunk for chunk in result.stdout.split(SEP + "\n") if chunk.strip()]
if len(rows) <= 1:
    rows = [chunk for chunk in result.stdout.split(SEP) if chunk.strip()]

total = 0
with_hits = 0
for chunk in rows:
    parts = chunk.split("\n", 1)
    if len(parts) != 2:
        continue
    path, escaped = parts[0].strip(), parts[1]
    content = escaped.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")
    total += 1
    hits = []
    for pattern, label in PATTERNS:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            start = max(0, match.start() - 55)
            end = min(len(content), match.end() + 55)
            hits.append((label, match.group(0), " ".join(content[start:end].split())))
    if hits:
        with_hits += 1
        print(f"=== {path}")
        seen = set()
        shown = 0
        for label, hit, context in hits:
            key = hit.lower()
            if key in seen or shown >= 5:
                continue
            seen.add(key)
            shown += 1
            print(f"  [{label}] {hit}  …{context}…")

print(f"\nscanned {total} session documents; {with_hits} contain in-world date references")
