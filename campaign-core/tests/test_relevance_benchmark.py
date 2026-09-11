import json

from tests.support.relevance_benchmark import (
    FIXTURE,
    FIXTURE_V2,
    baseline,
    baseline_v2,
    evaluate,
    evaluate_v2,
    fixture_v2_invariants,
)


def test_frozen_baseline_and_held_out_split():
    expected = json.loads(FIXTURE.with_name("relationship_relevance_baseline.json").read_text())
    assert baseline() == expected
    assert sum(c["split"] == "held_out" for c in expected["cases"]) == 4
    assert not expected["cases"][0]["pair_correct"]


def test_missing_coverage_separated_from_rank_failure():
    corpus = json.loads(FIXTURE.read_text())
    result = evaluate(corpus, {}, [])
    assert all(c["coverage_missing"] for c in result["cases"])
    assert all(not c["pair_correct"] for c in result["cases"])


def test_comparative_arm_is_not_mislabeled_as_lexical():
    corpus = json.loads(FIXTURE.read_text())
    assert evaluate(corpus, {}, [], arm="native-cognee")["arm"] == "native-cognee"


def test_v2_frozen_lexical_baseline_and_held_out_split():
    expected = json.loads(FIXTURE_V2.with_name("relationship_relevance_baseline_v2.json").read_text())
    assert baseline_v2() == expected
    assert sum(c["split"] == "held_out" for c in expected["cases"]) == 5
    organization = next(c for c in expected["cases"] if c["id"] == "organization")
    assert not organization["pair_correct"] and organization["bridge_coverage_missing"] == []


def test_v2_explicit_bridge_corpus_invariants():
    corpus = json.loads(FIXTURE_V2.read_text(encoding="utf-8"))
    result = fixture_v2_invariants(corpus)
    assert result["declared_chains"] == result["declared_chains_bridged"] >= 2
    assert result["forbidden_pairs"] >= 3
    assert result["forbidden_pairs_share_entity"] == []
    assert result["forbidden_pairs_connected"] == []


def test_bridge_coverage_is_separate_from_record_coverage():
    corpus = json.loads(FIXTURE_V2.read_text(encoding="utf-8"))
    indexed = [r["id"] for r in corpus["records"] if r["id"] != "company-bridge"]
    result = evaluate_v2(corpus, {"organization": ["command", "company"]}, indexed)
    row = next(c for c in result["cases"] if c["id"] == "organization")
    assert row["coverage_missing"] == ["company-bridge"]
    assert row["bridge_coverage_missing"] == ["command|company-bridge", "company-bridge|company"]
    assert row["recall_at_10"] == 2 / 3


def test_false_bridge_claims_counted_only_when_a_path_claims_them():
    corpus = json.loads(FIXTURE_V2.read_text(encoding="utf-8"))
    indexed = [r["id"] for r in corpus["records"]]
    question = {"absent-bridge-development": ["silver-helms"]}

    def row(result):
        return next(c for c in result["cases"] if c["id"] == "absent-bridge-development")

    clean = evaluate_v2(corpus, question, indexed,
                        {"absent-bridge-development": [["silver-helms"]]})
    claiming = evaluate_v2(corpus, question, indexed,
                           {"absent-bridge-development": [["silver-helms", "ossler-company"]]})
    assert row(clean)["false_bridge_claims"] == []
    assert row(claiming)["false_bridge_claims"] == ["ossler-company|silver-helms"]


def test_path_coverage_requires_the_full_chain_in_one_returned_path():
    corpus = json.loads(FIXTURE_V2.read_text(encoding="utf-8"))
    indexed = [r["id"] for r in corpus["records"]]
    chain = ["command", "company-bridge", "company"]
    whole = evaluate_v2(corpus, {"organization": chain}, indexed,
                         {"organization": [chain]})
    split = evaluate_v2(corpus, {"organization": chain}, indexed,
                        {"organization": [chain[:2], chain[1:]]})
    chainless = evaluate_v2(corpus, {"causality": ["power"]}, indexed)

    def row(result, identity):
        return next(c for c in result["cases"] if c["id"] == identity)

    assert row(whole, "organization")["path_covered"] is True
    assert row(split, "organization")["path_covered"] is False
    assert row(chainless, "causality")["path_covered"] is None
