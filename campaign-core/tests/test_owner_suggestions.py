"""Owner suggestions + the subjectless-commit guardrail (TKT-0148)."""

from uuid import UUID

from dm_assistant_core.application.owner_suggestions import (
    suggest_owner_matches,
)

ROMULUS = UUID("aa000000-0000-0000-0000-000000000002")
ARKIN = UUID("aa000000-0000-0000-0000-000000000003")
RAVENHOLDT = UUID("aa000000-0000-0000-0000-000000000004")


def test_matches_rank_longest_first_and_respect_limit_and_exclude():
    names = [
        (ROMULUS, "Romulus", "npc"),
        (ARKIN, "Arkin", "npc"),
        (RAVENHOLDT, "Ravenholdt", "location"),
    ]
    aliases: list[tuple] = []
    matches = suggest_owner_matches("Romulus rides to Ravenholdt.", names, aliases, limit=3)
    assert [(m.entity_id, m.entity_name) for m in matches] == [
        (RAVENHOLDT, "Ravenholdt"),  # longer name = more specific, first
        (ROMULUS, "Romulus"),
    ]
    capped = suggest_owner_matches("Romulus rides to Ravenholdt.", names, aliases, limit=1)
    assert [m.entity_name for m in capped] == ["Ravenholdt"]
    excluded = suggest_owner_matches(
        "Romulus rides to Ravenholdt.", names, aliases, limit=3, exclude={RAVENHOLDT}
    )
    assert [m.entity_name for m in excluded] == ["Romulus"]


def test_word_boundaries_prevent_substring_matches():
    names = [(UUID("aa000000-0000-0000-0000-000000000005"), "Art", "npc")]
    assert suggest_owner_matches("The artisan made a blade.", names, []) == []


def test_the_guardrail_refuses_subjectless_claims_without_a_disposition():
    from datetime import UTC, datetime
    from uuid import uuid4

    from dm_assistant_core.adapters.postgres.candidate_proposals import _validate_claim
    from dm_assistant_core.application.candidate_proposals import (
        CandidateProposalError,
        CreateClaimDecision,
    )
    from dm_assistant_core.domain import ClaimState, Visibility
    from dm_assistant_core.importer import CandidateAuthority

    def decision(**overrides):
        base = dict(
            mutation_kind="create_claim",
            candidate_id=uuid4(),
            evidence_revision_id=uuid4(),
            target_id=uuid4(),
            subject_entity_id=None,
            state=ClaimState.OBSERVED,
            authority=CandidateAuthority.REAL_PLAY,
            visibility=Visibility.DM_ONLY,
            confidence="1",
            is_conditional=False,
            predicts_subject_action=False,
            recorded_at=datetime.now(UTC),
            observed_at={"calendar_id": "gregorian-ce", "year": 505, "month": 10, "day": 20},
        )
        base.update(overrides)
        return CreateClaimDecision(**base)

    class FakeResult:
        @staticmethod
        def fetchone():
            return None

        @staticmethod
        def fetchall():
            return []

    class FakeConnection:
        def execute(self, sql, params=()):
            return FakeResult()

    candidate = (uuid4(), "", "observed", "real_play", "dm_only", False, False)
    try:
        _validate_claim(FakeConnection(), decision(), candidate, {}, uuid4())
    except CandidateProposalError as error:
        assert "needs its owning record" in str(error)
    else:
        raise AssertionError("the subjectless decision passed the guardrail")

    # With the explicit disposition the guardrail steps aside (the receipt
    # rides the change-set apply into claim_owner_dispositions).
    _validate_claim(
        FakeConnection(),
        decision(owner_disposition="No single record — ambient lore"),
        candidate,
        {},
        uuid4(),
    )
