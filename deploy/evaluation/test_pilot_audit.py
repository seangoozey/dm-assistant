from audit_pilot_bundle import audit


def test_missing_chunk_fails_coverage():
    report = audit({"records": [], "documents": {"missing": {"text": "original"}},
                    "graph": [[], []]})
    assert report["missing_documents"] == ["missing"]
    assert not report["passed"]


def test_coverage_alone_does_not_prove_discovery():
    report = audit({"records": [], "documents": {"doc": {"text": "original"}},
                    "graph": [[["chunk", {"type": "DocumentChunk", "document_id": "doc",
                                           "text": "original"}]], []]})
    assert not report["missing_documents"]
    assert not report["passed"]
