import pytest
from evidence_chunks import chunks


@pytest.mark.parametrize("text", ["", "hello", "A paragraph.\n\n# Heading\n" * 100, "✨" * 200])
def test_exact_coverage_and_bound(text):
    count = lambda value: len(value.encode())
    parts = list(chunks(text, count, 32))
    assert "".join(p["text"] for p in parts) == text
    for p in parts:
        assert p["text"] == text[p["start"]:p["end"]]
        assert count(p["text"]) <= 32
