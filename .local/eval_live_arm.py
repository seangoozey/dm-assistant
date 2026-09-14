"""Score the six draft v3-live judgments against the DEPLOYED retrieval stack
(bundle v5, lexical + graph walker). Free, local, no provider calls."""

import json
import subprocess
import urllib.request

ROOT = r"E:\dm-assistant"
corpus = json.load(open(ROOT + r"\.local\cognee-evaluation\relevance-v3-live-corpus.json", encoding="utf-8"))
records = {record["id"]: record for record in corpus["records"]}

# Corpus records were length-capped at export; resolve each corpus id by a
# distinctive tail slice so longer live claims still map correctly.
tails = {}
for corpus_id, record in records.items():
    tails.setdefault(" ".join(record["text"].split())[-70:], []).append(corpus_id)

def corpus_id_for(assertion):
    flat = " ".join(assertion.split())
    matches = [ids[0] for tail, ids in tails.items() if tail in flat and len(ids) == 1]
    return matches[-1] if len(set(matches)) == 1 else None

satisfied = 0
for case in corpus["cases"]:
    request = urllib.request.Request(
        "http://127.0.0.1:8001/retrieval/query",
        data=json.dumps({"question": case["question"], "requester_visibility": {"role": "dm"}}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request) as response:
        data = json.loads(response.read())
    ranks = {}
    for position, item in enumerate(data.get("evidence", []), start=1):
        corpus_id = corpus_id_for(item.get("assertion", ""))
        if corpus_id and corpus_id not in ranks:
            ranks[corpus_id] = position
    pref_rank = ranks.get(case["preferred"])
    over_rank = ranks.get(case["over"])
    missing = [r for r in case.get("required", []) if r not in ranks]
    ok = pref_rank is not None and (over_rank is None or pref_rank < over_rank) and not missing
    satisfied += ok
    print(f"  {case['id']:22s} {'PASS' if ok else 'FAIL'}  "
          f"preferred rank {pref_rank} vs over {over_rank}"
          + (f"  missing: {missing}" if missing else "")
          + ("" if pref_rank is not None else "  preferred absent"))
print(f"deployed stack (lexical + v5 walker): {satisfied}/{len(corpus['cases'])} draft judgments satisfied")
