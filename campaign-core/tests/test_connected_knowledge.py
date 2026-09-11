"""Validate the frozen cross-workflow corpus and deterministic baseline."""

import json
from collections import Counter

from tests.support.connected_knowledge_harness import FIXTURE, load, run


def test_connected_corpus_and_ordering():
    corpus = load()
    assert len(corpus.cases) >= 24
    counts = Counter(case.workflow for case in corpus.cases)
    assert all(counts[workflow] >= 4 for workflow in ("ask", "encounter", "lore", "brainstorm"))
    forward, backward = run(corpus), run(corpus, reverse=True)
    for result in (forward, backward):
        for case in result["cases"]:
            assert case.pop("policy_latency_ms") >= 0
            assert not case["forbidden_evidence"]
            assert not case["forbidden_support"]
            assert case["unsupported_connections"] is None
    assert forward == backward
    baseline = json.loads(FIXTURE.with_name("connected_knowledge_baseline.json").read_text())
    # Preserve the historical baseline. Only privacy cases change in this tranche;
    # their original restricted-mode gold itself disclosed hidden evidence.
    privacy_cases = {"security-hidden", "security-hidden-path"}
    for current, previous in zip(forward["cases"], baseline["cases"], strict=True):
        if current["id"] not in privacy_cases:
            assert current == previous
    without_hidden = corpus.model_copy(update={
        "records": [record for record in corpus.records if record.visibility == "party"]
    })
    public = run(without_hidden)
    for current, visible_only in zip(forward["cases"], public["cases"], strict=True):
        visible_only.pop("policy_latency_ms")
        if current["id"] in privacy_cases:
            assert current == visible_only
    # Missing relationship traversal and overly broad conflict checks are baseline
    # failures, not acceptable future targets or reasons to weaken expected cases.
    assert any(not case["mode_correct"] for case in forward["cases"])
    assert any(case["path_recall"] == 0 for case in forward["cases"])
