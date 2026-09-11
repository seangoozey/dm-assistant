"""Lossless token-budgeted passage slices, offsets relative to parent assertion."""
from hashlib import sha256


def chunks(text, token_count, limit=512):
    if limit < 1:
        raise ValueError("positive token limit required")
    start = 0
    while start < len(text):
        low, high = start + 1, len(text)
        end = start
        while low <= high:
            middle = (low + high) // 2
            if token_count(text[start:middle]) <= limit:
                end, low = middle, middle + 1
            else:
                high = middle - 1
        if end == start:
            raise ValueError("single character exceeds token limit")
        # Prefer a paragraph/section boundary within the latter half of the
        # budget, but never omit text. Parent evidence links supply context.
        if end < len(text):
            boundary = text.rfind("\n\n", start + (end - start) // 2, end)
            if boundary >= start:
                end = boundary + 2
        passage = text[start:end]
        yield {"start": start, "end": end, "text": passage,
               "hash": sha256(passage.encode()).hexdigest()}
        start = end
