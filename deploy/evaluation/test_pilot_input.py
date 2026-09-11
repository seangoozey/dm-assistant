from pilot_input import embedding_batches, index_text


def test_versioned_input_preserves_assertion_and_modality():
    record = {"assertion": "The captain plans to attack the port.",
              "state": "intended", "authority": "npc_intention"}
    assert index_text(record, "live-pilot-v2") == record["assertion"]
    text = index_text(record, "live-pilot-v3")
    assert text.endswith(record["assertion"])
    assert "Recorded state: intended" in text
    assert "NOT completed events" in text


def test_embedding_batches_preserve_all_text_with_byte_and_count_limits():
    texts = ["x" * 7000] * 10 + ["short"] * 50
    batches = list(embedding_batches(texts))
    assert [text for batch in batches for text in batch] == texts
    assert all(len(batch) <= 32 for batch in batches)
    assert len(batches) > 2
