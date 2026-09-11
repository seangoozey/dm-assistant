from dm_assistant_core.adapters.postgres.claim_reconciliation import claim_similarity


def test_exact_claims_are_overlap_candidates() -> None:
    assert claim_similarity("Ruhrogue may unite Myrin.", "Ruhrogue may unite Myrin.") == 1


def test_close_paraphrases_are_overlap_candidates() -> None:
    score = claim_similarity(
        "Ruhrogue may unite the peoples and nations of Myrin.",
        "Ruhrogue might unite Myrin's peoples and nations.",
    )
    assert score >= 0.62


def test_distinct_claims_can_legitimately_coexist_without_being_suggested() -> None:
    score = claim_similarity(
        "Ruhrogue trained under Ruh in Fleurite.",
        "Ruhrogue left Fleurite after Goodman's death.",
    )
    assert score < 0.62
