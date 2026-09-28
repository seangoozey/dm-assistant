"""Unit coverage for the Promotion Pipeline facade (ADR-0018, TKT-0136)."""

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from dm_assistant_core.application.candidate_proposals import (
    ApproveCandidateProposalCommand,
    CandidateProposalError,
    CandidateProposalService,
    CandidateProposalVersion,
    CreateCandidateProposalCommand,
    ReviseCandidateProposalCommand,
    assertions_require_conflict_review,
)
from dm_assistant_core.application.change_sets import ChangeSetApplicationService
from dm_assistant_core.domain import ClaimState, RequesterRole, RequesterVisibility
from dm_assistant_core.domain.change_sets import ChangeSetReceipt
from dm_assistant_core.application.promotion import (
    ApprovePromotionCommand,
    DerivePromotionCommand,
    PromotionSubject,
    PromotionCandidateList,
    PromotionCommitReceipt,
    PromotionError,
    PromotionService,
    PromotionStatement,
    restates_claim,
    split_statements,
)
from dm_assistant_core.application.promotion import ClaimSummary

DM = RequesterVisibility(role=RequesterRole.DM)
PARTY = RequesterVisibility(role=RequesterRole.PARTY)


def _claim(assertion: str, predicate: str | None = None) -> ClaimSummary:
    return ClaimSummary(claim_id=uuid4(), assertion_text=assertion, predicate=predicate)


# --- deterministic derivation -------------------------------------------------


def test_split_statements_offsets_address_the_text() -> None:
    text = "The Treasury funds the rebellion. Its vault lies beneath the palace!\n"
    statements = split_statements(text)
    assert [text[start:end] for start, end, _ in statements] == [
        "The Treasury funds the rebellion.",
        "Its vault lies beneath the palace!",
    ]
    for start, end, statement in statements:
        assert text[start:end] == statement


def test_split_statements_skips_blank_lines() -> None:
    statements = split_statements("\n\nOne claim.\n\n\nTwo claims.\n")
    assert [statement for _, _, statement in statements] == ["One claim.", "Two claims."]


def test_restates_claim_detects_mirror_not_passing_mention() -> None:
    mirror = _claim("The Fleurite Treasury funds the rebellion against the crown")
    assert restates_claim("The Treasury funds the rebellion", (mirror,)) is mirror
    assert restates_claim("The vault lies beneath the palace", (mirror,)) is None


def test_assertions_overlap_gate_is_narrow() -> None:
    assert assertions_require_conflict_review(
        "Ishi'ra'la serves the Grand Inquisitor", None,
        "Ishi'ra'la serves the Grand Inquisitor", None,
    )
    assert not assertions_require_conflict_review(
        "Person X is ugly", None, "Person X is cute", None
    )


# --- derive --------------------------------------------------------------------


class FakeReads:
    def __init__(self, existing=(), referenced=(), stored=None, items=()) -> None:
        self.existing = tuple(existing)
        self.referenced = tuple(referenced)
        self.stored = stored
        self.items = tuple(items)

    def claims_for_entity(self, entity_id):
        return self.existing

    def claims_by_ids(self, claim_ids):
        return self.referenced

    def change_set_for_key(self, idempotency_key):
        return self.stored

    def claim_targets_for_items(self, item_ids):
        return self.items


class FakeDescriptions:
    def __init__(self) -> None:
        self.commands = []

    def write(self, command):
        self.commands.append(command)
        return SimpleNamespace(
            document_id=uuid4(),
            revision_id=uuid4(),
            path=f"entities/{command.entity_id}.md",
            idempotent_replay=False,
            candidate_ids=tuple(uuid4() for _ in command.statement_spans),
        )


class FakeProposals:
    def __init__(self, create_error: Exception | None = None) -> None:
        self.created = None
        self.revised = None
        self.approved = None
        self.create_error = create_error
        from dm_assistant_core.application.candidate_proposals import (
            CandidateProposalItem,
            ProposalCandidateBinding,
        )

        item = CandidateProposalItem(
            item_id=uuid4(),
            sequence=1,
            mutation_kind="create_claim",
            target_type="claim",
            target_id=uuid4(),
            after={"assertion_text": "stub"},
            evidence=ProposalCandidateBinding(
                candidate_id=uuid4(),
                source_revision_id=uuid4(),
                source_span_id=uuid4(),
                candidate_fingerprint="b" * 64,
            ),
        )
        self.version = CandidateProposalVersion(
            proposal_id=uuid4(),
            workflow_session_id=uuid4(),
            status="pending",
            version_id=uuid4(),
            version_number=1,
            content_hash="a" * 64,
            supersedes_version_id=None,
            created_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            items=(item,),
        )

    def create(self, command, requester):
        if self.create_error is not None:
            raise self.create_error
        self.created = command
        return self.version

    def revise(self, command, requester):
        self.revised = command
        return self.version

    def get_for_candidate(self, candidate_id, requester):
        return self.version if self.create_error is not None else None

    def approve(self, command, requester):
        self.approved = command
        return SimpleNamespace(
            approval_id=uuid4(),
            change_set_id=uuid4(),
            idempotent_replay=False,
        )


class FakeChangeSets:
    def __init__(self) -> None:
        self.applied = []

    def apply(self, command):
        self.applied.append(command)
        return ChangeSetReceipt(
            receipt_id=uuid4(),
            change_set_id=command.change_set_id,
            outcome="applied",
            applied_item_ids=(uuid4(),),
            issued_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            idempotent_replay=False,
        )


def _entity(entity_id: UUID) -> SimpleNamespace:
    return SimpleNamespace(entity_id=entity_id, canonical_name="Fleurite Treasury")


class FakeEntityNames:
    def __init__(self, entity_id: UUID) -> None:
        self.entity_id = entity_id

    def get(self, value):
        return _entity(self.entity_id) if value == self.entity_id else None


def _service(reads=None, descriptions=None, proposals=None, change_sets=None):
    entity_id = uuid4()
    return (
        PromotionService(
            descriptions or FakeDescriptions(),
            proposals or FakeProposals(),  # type: ignore[arg-type]
            change_sets or FakeChangeSets(),  # type: ignore[arg-type]
            reads or FakeReads(),  # type: ignore[arg-type]
            FakeEntityNames(entity_id),  # type: ignore[arg-type]
        ),
        entity_id,
    )


def test_derive_marks_reference_and_conflict_candidates() -> None:
    mirror = _claim("The Fleurite Treasury funds the rebellion against the crown")
    clashing = _claim("The vault was destroyed during the siege of the city")
    service, entity_id = _service(
        reads=FakeReads(existing=(clashing,), referenced=(mirror,))
    )
    result = service.derive(
        DerivePromotionCommand(
            surface="description",
            entity_id=entity_id,
            document_text=(
                "The Treasury funds the rebellion. "
                "The vault was destroyed during the siege of the city. "
                "Its seals were forged by Fleurite exiles."
            ),
            referenced_claim_ids=(mirror.claim_id,),
        ),
        DM,
    )
    assert isinstance(result, PromotionCandidateList)
    assert result.entity_name == "Fleurite Treasury"
    assert [candidate.consequence.kind for candidate in result.candidates] == [
        "reference",
        "new_claim",
        "new_claim",
    ]
    assert result.candidates[0].included is False
    assert result.candidates[1].conflict is not None
    assert result.candidates[1].included is False
    assert result.candidates[2].conflict is None
    assert result.candidates[2].included is True
    assert result.candidates[2].state is ClaimState.ESTABLISHED


def test_derive_is_dm_only() -> None:
    service, entity_id = _service()
    with pytest.raises(PromotionError):
        service.derive(
            DerivePromotionCommand(
                surface="description",
                entity_id=entity_id,
                document_text="One statement.",
            ),
            PARTY,
        )


def test_approve_files_documents_without_candidates_when_nothing_included() -> None:
    descriptions = FakeDescriptions()
    service, entity_id = _service(descriptions=descriptions)
    receipt = service.approve_promotion(
        ApprovePromotionCommand(
            surface="description",
            entity_id=entity_id,
            document_text="One statement.",
            statements=(),
            idempotency_key="promo:test:1",
        ),
        DM,
    )
    assert isinstance(receipt, PromotionCommitReceipt)
    assert receipt.claims_committed == 0
    assert descriptions.commands[0].statement_spans == ()


def test_approve_commits_claims_and_description_in_one_action() -> None:
    descriptions = FakeDescriptions()
    proposals = FakeProposals()
    change_sets = FakeChangeSets()
    reads = FakeReads()
    entity_id = uuid4()
    service = PromotionService(
        descriptions,  # type: ignore[arg-type]
        proposals,  # type: ignore[arg-type]
        change_sets,  # type: ignore[arg-type]
        reads,  # type: ignore[arg-type]
        FakeEntityNames(entity_id),  # type: ignore[arg-type]
    )
    start, end = 0, len("The Treasury funds the rebellion.")
    reads.items = ((uuid4(), uuid4()),)
    receipt = service.approve_promotion(
        ApprovePromotionCommand(
            surface="description",
            entity_id=entity_id,
            document_text="The Treasury funds the rebellion. Flavor follows.",
            statements=(
                PromotionStatement(
                    span_start=start, span_end=end,
                    assertion_text="The Treasury funds the rebellion.",
                    state=ClaimState.ESTABLISHED,
                    included=True,
                ),
            ),
            idempotency_key="promo:test:2",
        ),
        DM,
    )
    assert receipt.claims_committed == 1
    assert descriptions.commands[0].statement_spans == ((start, end),)
    assert descriptions.commands[0].idempotency_key == "promo:test:2:file"
    assert proposals.created is not None
    decision = proposals.created.items[0]
    assert decision.state is ClaimState.ESTABLISHED
    assert decision.subject_entity_id == entity_id
    assert decision.assertion_text == "The Treasury funds the rebellion."
    assert proposals.approved.idempotency_key.startswith("promo:test:2:")
    assert len(change_sets.applied) == 1


def test_approve_converges_by_revising_when_candidates_already_proposed() -> None:
    proposals = FakeProposals(
        create_error=CandidateProposalError(
            "candidate review status proposed cannot be proposed"
        )
    )
    service, entity_id = _service(proposals=proposals)
    end = len("One statement.")
    service.approve_promotion(
        ApprovePromotionCommand(
            surface="description",
            entity_id=entity_id,
            document_text="One statement.",
            statements=(
                PromotionStatement(span_start=0, span_end=end, assertion_text="One statement."),
            ),
            idempotency_key="promo:test:3",
        ),
        DM,
    )
    assert proposals.revised is not None


def test_approve_rejects_state_not_offered_on_surface() -> None:
    service, entity_id = _service()
    end = len("One statement.")
    with pytest.raises(PromotionError, match="not offered"):
        service.approve_promotion(
            ApprovePromotionCommand(
                surface="description",
                entity_id=entity_id,
                document_text="One statement.",
                statements=(
                    PromotionStatement(
                        span_start=0, span_end=end,
                        assertion_text="One statement.",
                        state=ClaimState.OBSERVED,
                    ),
                ),
                idempotency_key="promo:test:4",
            ),
            DM,
        )


def test_approve_rejects_stale_spans_with_readable_error() -> None:
    service, entity_id = _service()
    with pytest.raises(PromotionError, match="review the promotion again"):
        service.approve_promotion(
            ApprovePromotionCommand(
                surface="description",
                entity_id=entity_id,
                document_text="Shorter text now.",
                statements=(
                    PromotionStatement(
                        span_start=0, span_end=400, assertion_text="Whatever."
                    ),
                ),
                idempotency_key="promo:test:5",
            ),
            DM,
        )


def test_considered_coordinate_passes_the_shared_gate() -> None:
    from dm_assistant_core.application.promotion import SURFACE_REGISTRY
    from dm_assistant_core.application.promotion import PromotionSurface

    config = SURFACE_REGISTRY[PromotionSurface.DESCRIPTION]
    assert config.state_overrides[ClaimState.CONSIDERED].value == "brainstorm"

# --- free-surface (brainstorm) ------------------------------------------------


def test_free_surface_requires_subjects_and_candidates() -> None:
    service, _ = _service()
    command = ApprovePromotionCommand(
        surface="brainstorm",
        document_text="irrelevant for free surfaces",
        statements=(
            PromotionStatement(
                span_start=0, span_end=10, assertion_text="A thought.",
            ),
        ),
        idempotency_key="promo:brainstorm:1",
    )
    with pytest.raises(PromotionError, match="workflow session"):
        service.approve_promotion(command, DM)
    command = command.model_copy(update={"workflow_session_id": uuid4()})
    with pytest.raises(PromotionError, match="subject"):
        service.approve_promotion(command, DM)


def test_free_surface_rejects_unoffered_state() -> None:
    service, _ = _service()
    subject = PromotionSubject(entity_id=uuid4())
    command = ApprovePromotionCommand(
        surface="brainstorm",
        document_text="irrelevant",
        workflow_session_id=uuid4(),
        statements=(
            PromotionStatement(
                span_start=0, span_end=10, assertion_text="A thought.",
                state=ClaimState.OBSERVED, subject=subject,
                candidate_id=uuid4(), evidence_revision_id=uuid4(),
            ),
        ),
        idempotency_key="promo:brainstorm:2",
    )
    with pytest.raises(PromotionError, match="not offered"):
        service.approve_promotion(command, DM)


def test_free_surface_mints_records_and_threads_the_workflow_session() -> None:
    from dm_assistant_core.application.promotion import (
        ApprovePromotionCommand as _Cmd,
    )

    descriptions = FakeDescriptions()
    proposals = FakeProposals()
    change_sets = FakeChangeSets()
    reads = FakeReads()

    minted_entities: list[tuple[str, str, str]] = []

    class MappingReads(FakeReads):
        def claim_targets_for_items(self, item_ids):
            return tuple((item_id, uuid4()) for item_id in item_ids)

    reads = MappingReads()

    class RecordingCreator:
        def create(self, surface, entity_kind, idempotency_key):
            minted_entities.append((surface, entity_kind, idempotency_key))
            return SimpleNamespace(entity_id=uuid4())

    entity_id = uuid4()
    service = PromotionService(
        descriptions,  # type: ignore[arg-type]
        proposals,  # type: ignore[arg-type]
        change_sets,  # type: ignore[arg-type]
        reads,  # type: ignore[arg-type]
        FakeEntityNames(entity_id),  # type: ignore[arg-type]
        entity_creator=RecordingCreator(),
    )
    workflow = uuid4()
    new_record_claim = uuid4()
    command = _Cmd(
        surface="brainstorm",
        document_text="joined thoughts",
        workflow_session_id=workflow,
        statements=(
            # An existing record subject.
            PromotionStatement(
                span_start=0, span_end=9, assertion_text="Thought A.",
                state=ClaimState.CONSIDERED,
                subject=PromotionSubject(entity_id=entity_id),
                candidate_id=uuid4(), evidence_revision_id=uuid4(),
            ),
            # Two statements sharing ONE new record.
            PromotionStatement(
                span_start=10, span_end=19, assertion_text="Thought B.",
                state=ClaimState.ESTABLISHED,
                subject=PromotionSubject(new_record="r1", name="Vault Guild", entity_kind="faction"),
                candidate_id=uuid4(), evidence_revision_id=uuid4(),
            ),
            PromotionStatement(
                span_start=20, span_end=29, assertion_text="Thought C.",
                state=ClaimState.ESTABLISHED,
                subject=PromotionSubject(new_record="r1", name="Vault Guild", entity_kind="faction"),
                candidate_id=new_record_claim, evidence_revision_id=uuid4(),
            ),
        ),
        idempotency_key="promo:brainstorm:3",
    )
    receipt = service.approve_promotion(command, DM)
    assert receipt.claims_committed == 1  # fake change set reports one item
    assert len(receipt.created_entity_ids) == 1  # r1 minted once, shared
    assert minted_entities == [("Vault Guild", "faction", "promo:brainstorm:3:r1:entity")]
    assert proposals.created is not None
    assert proposals.created.workflow_session_id == workflow
    decisions = proposals.created.items
    assert decisions[0].subject_entity_id == entity_id
    assert decisions[1].subject_entity_id == decisions[2].subject_entity_id
    assert decisions[1].subject_entity_id == receipt.created_entity_ids[0]
    assert decisions[0].state is ClaimState.CONSIDERED
    assert decisions[0].authority.value == "brainstorm"
    assert decisions[1].authority.value == "explicit_lore"
    # No document is filed on the free surface.
    assert descriptions.commands == []

