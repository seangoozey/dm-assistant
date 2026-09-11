"""Deterministic, versioned index text; original assertions remain authoritative."""
import json


def embedding_batches(texts):
    batch, size = [], 0
    for text in texts:
        text_size = len(json.dumps(text).encode("utf-8")) + 2
        if text_size > 24000:
            raise ValueError("single embedding input exceeds safe byte limit")
        if batch and (len(batch) >= 32 or size + text_size > 24000):
            yield batch
            batch, size = [], 0
        batch.append(text)
        size += text_size
    if batch:
        yield batch


def index_text(record, generation):
    if generation == "live-pilot-v2":
        return record["assertion"]
    return (
        "Campaign evidence for relationship discovery. Preserve the source's modality: "
        "orders, plans, possibilities, and prepared outcomes are NOT completed events. "
        "A record's state does not make every embedded plan an observed outcome.\n"
        f"Recorded state: {record['state']}\nAuthority: {record['authority']}\n"
        "Source assertion (retain qualifications and negations):\n"
        + record["assertion"]
    )
