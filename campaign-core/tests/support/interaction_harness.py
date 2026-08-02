"""Load sanitized interaction fixtures and execute registered Core assertions."""

from collections.abc import Callable
from pathlib import Path

import yaml

from dm_assistant_core.acceptance import (
    DeterministicAssertion,
    InteractionCase,
    InteractionFixture,
)
from dm_assistant_core.domain import (
    ClaimState,
    ConflictOutcome,
    StaleApprovalError,
    Visibility,
    create_approval_scope,
    create_bounded_read_aloud,
    represent_pc_campaign_direction,
    resolve_explicit_candidate_revision,
    resolve_observed_conflict,
    scope_direct_lore_update,
    validate_current_approval,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPOSITORY_ROOT / "tests" / "fixtures" / "interaction_cases.yaml"

AssertionRunner = Callable[[InteractionCase], None]


def load_interaction_fixture(path: Path = FIXTURE_PATH) -> InteractionFixture:
    raw_fixture = yaml.safe_load(path.read_text(encoding="utf-8"))
    return InteractionFixture.model_validate(raw_fixture)


def assert_approval_scope_is_exact(case: InteractionCase) -> None:
    assert case.input
    approval = create_approval_scope(
        proposal_id="proposal-1",
        reviewed_version=3,
        visible_item_ids=("jace", "sibling-a", "sibling-b"),
        selected_item_ids=("jace",),
    )
    assert approval.item_ids == ("jace",)


def assert_creative_artifact_cannot_mutate_lore(case: InteractionCase) -> None:
    decision = create_bounded_read_aloud(case.input)
    assert decision.artifact_kind == "read_aloud"
    assert decision.canonical_mutation_allowed is False


def assert_approval_binds_to_current_version(case: InteractionCase) -> None:
    assert case.input
    old_approval = create_approval_scope(
        proposal_id="proposal-1",
        reviewed_version=1,
        visible_item_ids=("claim-1", "claim-2"),
        selected_item_ids=("claim-1", "claim-2"),
    )
    try:
        validate_current_approval(old_approval, proposal_id="proposal-1", current_version=2)
    except StaleApprovalError:
        pass
    else:
        raise AssertionError("approval of the prior proposal version was accepted")

    current_approval = old_approval.model_copy(update={"version": 2})
    validate_current_approval(current_approval, proposal_id="proposal-1", current_version=2)


def assert_pc_direction_is_conditional(case: InteractionCase) -> None:
    claim = represent_pc_campaign_direction(case.input)
    assert claim.state is ClaimState.PREPARED
    assert claim.visibility is Visibility.DM_ONLY
    assert claim.conditional is True
    assert claim.predicts_pc_action is False


def assert_observed_supersedes_prepared(case: InteractionCase) -> None:
    assert case.input
    decision = resolve_observed_conflict(ClaimState.PREPARED)
    assert decision.outcome is ConflictOutcome.SUPERSEDE_PREPARATION
    assert decision.incoming_state is ClaimState.OBSERVED
    assert decision.retain_prior is True
    assert decision.receipt_required is True
    assert decision.review_required is False


def assert_explicit_revision_supersedes_candidate(case: InteractionCase) -> None:
    earlier, separator, later = case.input.partition("Later:")
    assert separator
    decision = resolve_explicit_candidate_revision(
        earlier,
        later,
        explicit_correction="No," in later,
    )
    assert decision.earlier_state is ClaimState.SUPERSEDED
    assert decision.later_state is ClaimState.PROPOSED
    assert decision.canonical_mutation_allowed is False


def assert_direct_lore_preserves_parent(case: InteractionCase) -> None:
    decision = scope_direct_lore_update("brainstorm-1", "sorin")
    assert case.input
    assert decision.target_id == "sorin"
    assert decision.canonical_mutation_allowed is True
    assert decision.return_to_parent is True
    assert decision.sibling_proposal_items_authorized is False


ASSERTION_RUNNERS: dict[DeterministicAssertion, AssertionRunner] = {
    DeterministicAssertion.APPROVAL_SCOPE_IS_EXACT: assert_approval_scope_is_exact,
    DeterministicAssertion.CREATIVE_ARTIFACT_CANNOT_MUTATE_LORE: (
        assert_creative_artifact_cannot_mutate_lore
    ),
    DeterministicAssertion.APPROVAL_BINDS_TO_CURRENT_VERSION: (
        assert_approval_binds_to_current_version
    ),
    DeterministicAssertion.PC_DIRECTION_IS_CONDITIONAL: assert_pc_direction_is_conditional,
    DeterministicAssertion.OBSERVED_SUPERSEDES_PREPARED: assert_observed_supersedes_prepared,
    DeterministicAssertion.EXPLICIT_REVISION_SUPERSEDES_CANDIDATE: (
        assert_explicit_revision_supersedes_candidate
    ),
    DeterministicAssertion.DIRECT_LORE_PRESERVES_PARENT: assert_direct_lore_preserves_parent,
}


def execute_deterministic_assertions(case: InteractionCase) -> int:
    for assertion in case.deterministic_assertions:
        ASSERTION_RUNNERS[assertion](case)
    return len(case.deterministic_assertions)
