from dm_assistant_core.adapters.postgres.retrieval import _CANDIDATES_SQL, _CLAIMS_SQL
from dm_assistant_core.application.candidate_proposals import (
    assertions_require_conflict_review as _assertions_require_conflict_review,
)


def test_claim_retrieval_searches_assertion_subject_and_aliases() -> None:
    assert "c.assertion_text" in _CLAIMS_SQL
    assert "LEFT JOIN entities e ON e.id = c.subject_entity_id" in _CLAIMS_SQL
    assert "e.canonical_name" in _CLAIMS_SQL
    assert "string_agg(ea.alias" in _CLAIMS_SQL
    assert "ic.assertion_text" in _CANDIDATES_SQL


def test_unindexed_exact_assertion_still_requires_conflict_review() -> None:
    assertion = "Ruhrogue left Fleurite after Ruh died."

    assert _assertions_require_conflict_review(assertion, None, assertion, None)


def test_same_predicate_without_overlapping_meaning_is_not_a_conflict() -> None:
    assert not _assertions_require_conflict_review(
        "Ruhrogue left Fleurite after Ruh died.",
        "left",
        "Ruh left The Ocho before Goodman arrived.",
        "left",
    )


def test_same_subject_predicate_and_overlapping_assertion_requires_review() -> None:
    assert _assertions_require_conflict_review(
        "Ruhrogue killed Goodman in revenge at The Ocho.",
        "killed",
        "Ruhrogue killed Goodman during the mission at The Ocho.",
        "killed",
    )
