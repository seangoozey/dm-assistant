"""Promotion Pipeline facade (ADR-0018, TKT-0136).

One reusable Proposal -> Candidate -> Claim progression behind every surface
that turns working material into canon. The facade composes the existing
machinery — direct-input filing, candidate proposals, approvals, change-set
application — behind two operations:

- ``derive`` (a read): deterministically split the proposal text into atomic
  candidates, fill surface defaults, and run the narrow conflict pre-check.
- ``approve_promotion`` (single-action binding): file the document with
  candidates for the included statements, create or revise the immutable
  proposal version, bind approval to exactly that version, and apply the
  change set. One user action, one receipt, convergent on retry.

Surfaces adopt by declaring a config in ``SURFACE_REGISTRY`` (ownership model,
defaults, allowed state overrides, bundle label) — a configuration, not new
machinery.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from dm_assistant_core.application.candidate_proposals import (
    ApproveCandidateProposalCommand,
    CandidateProposalError,
    CandidateProposalService,
    CandidateProposalVersion,
    CreateCandidateProposalCommand,
    CreateClaimDecision,
    ProposalItemDecision,
    ReviseCandidateProposalCommand,
    assertions_require_conflict_review,
)
from dm_assistant_core.application.change_sets import ChangeSetApplicationService
from dm_assistant_core.application.claim_reattribution import ReattributeClaim
from dm_assistant_core.application.entity_descriptions import EntityDescriptionCommand
from dm_assistant_core.domain import ClaimState, RequesterRole, RequesterVisibility, Visibility
from dm_assistant_core.domain.change_sets import ApplyChangeSetCommand
from dm_assistant_core.importer import CandidateAuthority


class PromotionError(ValueError):
    """A promotion command failed a deterministic rule; the message is user-facing."""


class PromotionSurface(StrEnum):
    DESCRIPTION = "description"
    LORE = "lore"
    BRAINSTORM = "brainstorm"


class OwnershipModel(StrEnum):
    BOUND_EXISTING = "bound_existing"
    BOUND_CREATED = "bound_created"
    FREE = "free"


class SurfaceConfig(BaseModel):
    """The four-part adoption declaration for one consuming surface."""

    model_config = ConfigDict(frozen=True)

    surface: PromotionSurface
    ownership: OwnershipModel
    default_state: ClaimState
    default_authority: CandidateAuthority
    bundle_label: str
    # Truth States the DM may switch a candidate to inline, with the
    # authority each state pairs with (the coordinate gate in the proposal
    # adapter enforces the same pairs at commit time).
    state_overrides: dict[ClaimState, CandidateAuthority]


SURFACE_REGISTRY: dict[PromotionSurface, SurfaceConfig] = {
    PromotionSurface.DESCRIPTION: SurfaceConfig(
        surface=PromotionSurface.DESCRIPTION,
        ownership=OwnershipModel.BOUND_EXISTING,
        default_state=ClaimState.ESTABLISHED,
        default_authority=CandidateAuthority.EXPLICIT_LORE,
        bundle_label="description",
        state_overrides={
            ClaimState.ESTABLISHED: CandidateAuthority.EXPLICIT_LORE,
            ClaimState.CONSIDERED: CandidateAuthority.BRAINSTORM,
            ClaimState.PREPARED: CandidateAuthority.PREPARATION,
        },
    ),
    # Free-subject (ADR-0018 ownership models): no owner — each candidate
    # resolves its own subject, existing or newly created in the same commit.
    # Brainstorm statements are thought candidates: the proposal binds to the
    # brainstorm workflow session (the authority-strengthening exception keys
    # on it), and no document is filed.
    PromotionSurface.BRAINSTORM: SurfaceConfig(
        surface=PromotionSurface.BRAINSTORM,
        ownership=OwnershipModel.FREE,
        default_state=ClaimState.CONSIDERED,
        default_authority=CandidateAuthority.BRAINSTORM,
        bundle_label="records",
        state_overrides={
            ClaimState.CONSIDERED: CandidateAuthority.BRAINSTORM,
            ClaimState.POSSIBLE: CandidateAuthority.BRAINSTORM,
            ClaimState.ESTABLISHED: CandidateAuthority.EXPLICIT_LORE,
            ClaimState.INTENDED: CandidateAuthority.NPC_INTENTION,
            ClaimState.PREPARED: CandidateAuthority.PREPARATION,
        },
    ),
    # Bound-created (ADR-0018 ownership models): the owner does not exist
    # until the commit creates it. Lore ships with NO bypass — every creation
    # goes through promotion review from day one (mandatory-review ruling).
    PromotionSurface.LORE: SurfaceConfig(
        surface=PromotionSurface.LORE,
        ownership=OwnershipModel.BOUND_CREATED,
        default_state=ClaimState.ESTABLISHED,
        default_authority=CandidateAuthority.EXPLICIT_LORE,
        bundle_label="new record",
        state_overrides={
            ClaimState.ESTABLISHED: CandidateAuthority.EXPLICIT_LORE,
            ClaimState.CONSIDERED: CandidateAuthority.BRAINSTORM,
            ClaimState.PREPARED: CandidateAuthority.PREPARATION,
        },
    ),
}


class ClaimSummary(BaseModel):
    """The narrow claim read the derive pre-check needs."""

    model_config = ConfigDict(frozen=True)

    claim_id: UUID
    assertion_text: str
    predicate: str | None = None


class StoredChangeSet(BaseModel):
    """A change set already bound to this promotion's idempotency key."""

    model_config = ConfigDict(frozen=True)

    change_set_id: UUID
    status: str
    reviewed_version: int
    approval_id: UUID
    content_hash: str
    proposal_id: UUID


class PromotionReadRepository(Protocol):
    def claims_for_entity(self, entity_id: UUID) -> tuple[ClaimSummary, ...]: ...

    def claims_by_ids(self, claim_ids: tuple[UUID, ...]) -> tuple[ClaimSummary, ...]: ...

    def change_set_for_key(self, idempotency_key: str) -> StoredChangeSet | None: ...

    def claim_targets_for_items(
        self, item_ids: tuple[UUID, ...]
    ) -> tuple[tuple[UUID, UUID], ...]:
        """Map proposal item IDs to their (item_id, claim target_id) pairs."""
        ...

    def entity_id_by_canonical_name(self, name: str) -> UUID | None: ...


class EntityNameLookup(Protocol):
    def get(self, entity_id: UUID) -> object | None: ...


class EntityCreator(Protocol):
    """Receipted, idempotent entity creation (the identity-queue path)."""

    def create(self, surface: str, entity_kind: str, idempotency_key: str) -> object: ...


# --- deterministic derivation -------------------------------------------------

# The same statement splitter the session-note capture uses: line-bounded
# sentences ending on ., !, or ? so offsets always address the filed text.
_LINE_RE = re.compile(r"(?m)^[^\r\n]*\S[^\r\n]*")
_SENTENCE_RE = re.compile(r".+?(?:[.!?]+(?=\s|$)|$)")


def split_statements(text: str) -> list[tuple[int, int, str]]:
    """Split prose into (start, end, text) statements; offsets address ``text``."""
    statements: list[tuple[int, int, str]] = []
    for line_match in _LINE_RE.finditer(text):
        for match in _SENTENCE_RE.finditer(line_match.group()):
            raw = match.group()
            if not raw.strip():
                continue
            left_trim = len(raw) - len(raw.lstrip())
            right_trim = len(raw.rstrip())
            start = line_match.start() + match.start() + left_trim
            end = line_match.start() + match.start() + right_trim
            statements.append((start, end, text[start:end]))
    return statements


def _terms(value: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9]+", value.casefold()) if len(word) > 2}


def restates_claim(
    statement: str, claims: tuple[ClaimSummary, ...]
) -> ClaimSummary | None:
    """Return the referenced claim a statement merely restates, if any.

    A statement restates a claim when its term set and the claim's term set
    overlap heavily (the mirror the description gathered); passing mention of
    the same subject is not a restatement.
    """
    statement_terms = _terms(statement)
    if not statement_terms:
        return None
    for claim in claims:
        claim_terms = _terms(claim.assertion_text)
        if not claim_terms:
            continue
        union = statement_terms | claim_terms
        if len(statement_terms & claim_terms) / len(union) >= 0.5:
            return claim
    return None


class DerivePromotionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    surface: PromotionSurface
    entity_id: UUID | None = None  # bound-existing surfaces
    entity_name: str | None = None  # bound-created surfaces (lore)
    entity_kind: str | None = None  # bound-created surfaces (lore)
    document_text: str = Field(min_length=1)
    referenced_claim_ids: tuple[UUID, ...] = ()


class CandidateConsequence(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: str  # "new_claim" | "reference"
    claim_id: UUID | None = None
    label: str


class CandidateConflict(BaseModel):
    model_config = ConfigDict(frozen=True)

    against_claim_id: UUID
    against_text: str
    note: str = "overlaps an existing claim on this record — reword or exclude"


class PromotionCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    sequence: int = Field(gt=0)
    span_start: int = Field(ge=0)
    span_end: int = Field(gt=0)
    assertion_text: str = Field(min_length=1)
    state: ClaimState
    authority: CandidateAuthority
    consequence: CandidateConsequence
    conflict: CandidateConflict | None = None
    included: bool


class PromotionCandidateList(BaseModel):
    model_config = ConfigDict(frozen=True)

    surface: PromotionSurface
    ownership: OwnershipModel
    entity_id: UUID | None = None
    entity_name: str
    candidates: tuple[PromotionCandidate, ...]


class PromotionSubject(BaseModel):
    """A free-surface subject: an existing record, or one this commit mints.

    Bundle-local keys (new_record) are resolved server-side inside the
    approve action — the client never handles provisional UUIDs.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    entity_id: UUID | None = None
    new_record: str | None = None
    name: str | None = None
    entity_kind: str | None = None


class PromotionStatement(BaseModel):
    """One candidate row as the DM reviewed it, sent back on commit."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    span_start: int = Field(ge=0)
    span_end: int = Field(gt=0)
    assertion_text: str = Field(min_length=1)
    state: ClaimState = ClaimState.ESTABLISHED
    included: bool = True
    # Free surfaces (brainstorm): the reviewed subject and the thought
    # candidate this statement promotes.
    subject: PromotionSubject | None = None
    candidate_id: UUID | None = None
    evidence_revision_id: UUID | None = None


class ApprovePromotionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    surface: PromotionSurface
    entity_id: UUID | None = None  # bound-existing surfaces
    entity_name: str | None = None  # bound-created surfaces (lore)
    entity_kind: str | None = None  # bound-created surfaces (lore)
    document_text: str = Field(min_length=1)
    statements: tuple[PromotionStatement, ...] = ()
    referenced_claim_ids: tuple[UUID, ...] = ()
    linked_claim_ids: tuple[UUID, ...] = ()  # lore: assertions moving to the new record
    document_id: UUID | None = None  # set when revising an existing description
    workflow_session_id: UUID | None = None  # brainstorm: binds the proposal
    idempotency_key: str = Field(min_length=1)


class PromotionCommitReceipt(BaseModel):
    model_config = ConfigDict(frozen=True)

    entity_id: UUID
    entity_name: str
    document_id: UUID
    revision_id: UUID
    path: str
    claims_committed: int
    claim_ids: tuple[UUID, ...] = ()
    proposal_id: UUID | None = None
    change_set_id: UUID | None = None
    receipt_id: UUID | None = None
    moved_claim_ids: tuple[UUID, ...] = ()
    move_errors: tuple[str, ...] = ()
    created_entity_ids: tuple[UUID, ...] = ()
    idempotent_replay: bool


class PromotionService:
    def __init__(
        self,
        descriptions,
        proposals: CandidateProposalService,
        change_sets: ChangeSetApplicationService,
        reads: PromotionReadRepository,
        entity_names: EntityNameLookup,
        entity_creator: EntityCreator | None = None,
        reattribution=None,
    ) -> None:
        self._descriptions = descriptions
        self._proposals = proposals
        self._change_sets = change_sets
        self._reads = reads
        self._entity_names = entity_names
        self._entity_creator = entity_creator
        self._reattribution = reattribution

    # -- derive (a read) ------------------------------------------------------

    def derive(
        self, command: DerivePromotionCommand, requester: RequesterVisibility
    ) -> PromotionCandidateList:
        self._require_dm(requester)
        config = SURFACE_REGISTRY[command.surface]
        existing: tuple[ClaimSummary, ...] = ()
        if config.ownership is OwnershipModel.BOUND_EXISTING:
            if command.entity_id is None:
                raise PromotionError("this surface derives against an existing record")
            entity = self._entity_names.get(command.entity_id)
            if entity is None:
                raise PromotionError("no identity matches that entity")
            entity_name = str(getattr(entity, "canonical_name", ""))
            existing = self._reads.claims_for_entity(command.entity_id)
        elif config.ownership is OwnershipModel.BOUND_CREATED:
            if not command.entity_name or not command.entity_kind:
                raise PromotionError(
                    "bound-created surfaces derive with a name and kind"
                )
            entity_name = command.entity_name.strip()
            # No entity yet, so no existing-claims conflict pre-check; the
            # commit-time validation covers the created record.
        elif config.ownership is OwnershipModel.FREE:
            entity_name = "free subjects"
        else:
            raise PromotionError(f"surface {command.surface.value} derives elsewhere")
        referenced = (
            self._reads.claims_by_ids(command.referenced_claim_ids)
            if command.referenced_claim_ids
            else ()
        )
        candidates: list[PromotionCandidate] = []
        for sequence, (start, end, text) in enumerate(
            split_statements(command.document_text), start=1
        ):
            mirror = restates_claim(text, referenced)
            if mirror is not None:
                candidates.append(
                    PromotionCandidate(
                        sequence=sequence,
                        span_start=start,
                        span_end=end,
                        assertion_text=text,
                        state=config.default_state,
                        authority=config.default_authority,
                        consequence=CandidateConsequence(
                            kind="reference",
                            claim_id=mirror.claim_id,
                            label=f"restates claim {str(mirror.claim_id)[:8]} — "
                            "reference only, never a second claim",
                        ),
                        included=False,
                    )
                )
                continue
            conflict = None
            for claim in existing:
                if assertions_require_conflict_review(text, None, claim.assertion_text, claim.predicate):
                    conflict = CandidateConflict(
                        against_claim_id=claim.claim_id, against_text=claim.assertion_text
                    )
                    break
            candidates.append(
                PromotionCandidate(
                    sequence=sequence,
                    span_start=start,
                    span_end=end,
                    assertion_text=text,
                    state=config.default_state,
                    authority=config.default_authority,
                    consequence=CandidateConsequence(
                        kind="new_claim",
                        label=(
                            "new claim — subject required"
                            if config.ownership is OwnershipModel.FREE
                            else "new claim on this record"
                        ),
                    ),
                    conflict=conflict,
                    included=conflict is None,
                )
            )
        return PromotionCandidateList(
            surface=command.surface,
            ownership=config.ownership,
            entity_id=command.entity_id,
            entity_name=entity_name,
            candidates=tuple(candidates),
        )

    # -- approve promotion (single-action binding) -----------------------------

    def approve_promotion(
        self, command: ApprovePromotionCommand, requester: RequesterVisibility
    ) -> PromotionCommitReceipt:
        self._require_dm(requester)
        config = SURFACE_REGISTRY[command.surface]
        if config.ownership is OwnershipModel.FREE:
            return self._approve_free(command, requester, config)
        if config.ownership is OwnershipModel.BOUND_EXISTING:
            if command.entity_id is None:
                raise PromotionError("this surface promotes onto an existing record")
            entity = self._entity_names.get(command.entity_id)
            if entity is None:
                raise PromotionError("no identity matches that entity")
            entity_id: UUID | None = command.entity_id
            entity_name = str(getattr(entity, "canonical_name", ""))
        elif config.ownership is OwnershipModel.BOUND_CREATED:
            if not command.entity_name or not command.entity_kind:
                raise PromotionError("bound-created promotion needs a name and kind")
            entity_id = None
            entity_name = command.entity_name.strip()
        else:
            raise PromotionError(f"surface {command.surface.value} approves elsewhere")

        # Replay short-circuit: a change set already bound to this key means a
        # prior attempt reached approval. Apply is safe to retry, so finish it.
        stored = self._reads.change_set_for_key(command.idempotency_key)
        if stored is not None:
            return self._finish_stored(command, entity_id, entity_name, stored)

        statements = self._validated_statements(command, config)
        if entity_id is None:
            entity_id = self._ensure_entity(command, entity_name)
        file_receipt = self._descriptions.write(
            self._description_command(command, entity_id, statements)
        )
        included = [statement for statement in statements if statement.included]
        if not included:
            moved_claim_ids, move_errors = self._move_linked(command, entity_id, entity_name)
            return PromotionCommitReceipt(
                entity_id=entity_id,
                entity_name=entity_name,
                document_id=file_receipt.document_id,
                revision_id=file_receipt.revision_id,
                path=file_receipt.path,
                claims_committed=0,
                moved_claim_ids=moved_claim_ids,
                move_errors=move_errors,
                idempotent_replay=file_receipt.idempotent_replay,
            )

        candidate_ids = file_receipt.candidate_ids
        if len(candidate_ids) != len(included):
            raise PromotionError(
                "the filed statements and reviewed candidates differ — "
                "review the promotion again"
            )
        version = self._create_or_revise(
            command, entity_id, included, candidate_ids, file_receipt.revision_id
        )
        scope = tuple(item.item_id for item in version.items)
        approval = self._proposals.approve(
            ApproveCandidateProposalCommand(
                proposal_id=version.proposal_id,
                reviewed_version=version.version_number,
                content_hash=version.content_hash,
                item_ids=scope,
                idempotency_key=(
                    f"{command.idempotency_key}:"
                    f"{version.proposal_id}:v{version.version_number}"
                ),
            ),
            requester,
        )
        receipt = self._change_sets.apply(
            ApplyChangeSetCommand(
                change_set_id=approval.change_set_id,
                reviewed_version=version.version_number,
                approval_id=approval.approval_id,
                content_hash=version.content_hash,
            )
        )
        claim_ids = self._claim_ids(receipt.applied_item_ids)
        moved_claim_ids, move_errors = self._move_linked(command, entity_id, entity_name)
        return PromotionCommitReceipt(
            entity_id=entity_id,
            entity_name=entity_name,
            document_id=file_receipt.document_id,
            revision_id=file_receipt.revision_id,
            path=file_receipt.path,
            claims_committed=len(claim_ids),
            claim_ids=claim_ids,
            proposal_id=version.proposal_id,
            change_set_id=approval.change_set_id,
            receipt_id=receipt.receipt_id,
            moved_claim_ids=moved_claim_ids,
            move_errors=move_errors,
            idempotent_replay=receipt.idempotent_replay,
        )

    def _approve_free(
        self,
        command: ApprovePromotionCommand,
        requester: RequesterVisibility,
        config: SurfaceConfig,
    ) -> PromotionCommitReceipt:
        """Free-surface commit (brainstorm): statements are thought
        candidates, each with its reviewed subject; new records are minted
        once per bundle key inside this action. No document is filed."""
        if not command.workflow_session_id:
            raise PromotionError("free-surface promotion needs its workflow session")
        included = [s for s in command.statements if s.included]
        if not included:
            raise PromotionError(
                "a free-surface promotion requires at least one included statement"
            )
        for statement in included:
            if statement.subject is None:
                raise PromotionError("every included statement needs its subject")
            if statement.candidate_id is None or statement.evidence_revision_id is None:
                raise PromotionError(
                    "every included statement needs its thought candidate binding"
                )
            if statement.state not in config.state_overrides:
                raise PromotionError(
                    f"truth state {statement.state.value} is not offered on this surface"
                )

        stored = self._reads.change_set_for_key(command.idempotency_key)
        if stored is not None:
            return self._finish_stored_free(command, stored)

        # Resolve subjects: existing ids pass through; new_record keys mint
        # once (idempotent per promotion key) so several statements can share
        # one new record.
        minted: dict[str, UUID] = {}
        for statement in included:
            subject = statement.subject
            if subject.new_record is not None and subject.new_record not in minted:
                if not subject.name or not subject.entity_kind:
                    raise PromotionError(
                        "a new-record subject needs a name and kind"
                    )
                minted[subject.new_record] = self._ensure_entity(
                    type("Cmd", (), {
                        "entity_kind": subject.entity_kind,
                        # Per-record mint key so one promotion can mint several
                        # records, each stable across retries.
                        "idempotency_key": f"{command.idempotency_key}:{subject.new_record}",
                    })(),
                    subject.name.strip(),
                )

        items: tuple[ProposalItemDecision, ...] = tuple(
            CreateClaimDecision(
                mutation_kind="create_claim",
                candidate_id=statement.candidate_id,
                evidence_revision_id=statement.evidence_revision_id,
                target_id=uuid4(),
                subject_entity_id=(
                    statement.subject.entity_id
                    if statement.subject.entity_id is not None
                    else minted[statement.subject.new_record]
                ),
                assertion_text=statement.assertion_text.strip(),
                state=statement.state,
                authority=config.state_overrides[statement.state],
                visibility=Visibility.DM_ONLY,
                confidence=Decimal("1"),
                is_conditional=False,
                predicts_subject_action=False,
                recorded_at=datetime.now(UTC),
            )
            for statement in included
        )
        try:
            version = self._proposals.create(
                CreateCandidateProposalCommand(
                    workflow_session_id=command.workflow_session_id,
                    items=items,
                ),
                self._dm(),
            )
        except CandidateProposalError as error:
            if "cannot be proposed" not in str(error) and "already has a promotion proposal" not in str(error):
                raise
            existing = self._proposals.get_for_candidate(
                items[0].candidate_id, self._dm()
            )
            if existing is None:
                raise
            version = self._proposals.revise(
                ReviseCandidateProposalCommand(
                    proposal_id=existing.proposal_id, items=items
                ),
                self._dm(),
            )
        scope = tuple(item.item_id for item in version.items)
        approval = self._proposals.approve(
            ApproveCandidateProposalCommand(
                proposal_id=version.proposal_id,
                reviewed_version=version.version_number,
                content_hash=version.content_hash,
                item_ids=scope,
                idempotency_key=(
                    f"{command.idempotency_key}:"
                    f"{version.proposal_id}:v{version.version_number}"
                ),
            ),
            requester,
        )
        receipt = self._change_sets.apply(
            ApplyChangeSetCommand(
                change_set_id=approval.change_set_id,
                reviewed_version=version.version_number,
                approval_id=approval.approval_id,
                content_hash=version.content_hash,
            )
        )
        claim_ids = self._claim_ids(receipt.applied_item_ids)
        first_subject_name = next(
            (s.subject.name for s in included if s.subject.name), "records"
        )
        return PromotionCommitReceipt(
            entity_id=next(iter(minted.values())) if minted else (
                included[0].subject.entity_id if included[0].subject.entity_id else uuid4()
            ),
            entity_name=first_subject_name,
            document_id=uuid4(),
            revision_id=uuid4(),
            path="",
            claims_committed=len(claim_ids),
            claim_ids=claim_ids,
            proposal_id=version.proposal_id,
            change_set_id=approval.change_set_id,
            receipt_id=receipt.receipt_id,
            created_entity_ids=tuple(minted.values()),
            idempotent_replay=receipt.idempotent_replay,
        )

    def _finish_stored_free(
        self, command: ApprovePromotionCommand, stored: StoredChangeSet
    ) -> PromotionCommitReceipt:
        receipt = self._change_sets.apply(
            ApplyChangeSetCommand(
                change_set_id=stored.change_set_id,
                reviewed_version=stored.reviewed_version,
                approval_id=stored.approval_id,
                content_hash=stored.content_hash,
            )
        )
        claim_ids = self._claim_ids(receipt.applied_item_ids)
        return PromotionCommitReceipt(
            entity_id=stored.proposal_id,
            entity_name="records",
            document_id=uuid4(),
            revision_id=uuid4(),
            path="",
            claims_committed=len(claim_ids),
            claim_ids=claim_ids,
            proposal_id=stored.proposal_id,
            change_set_id=stored.change_set_id,
            receipt_id=receipt.receipt_id,
            created_entity_ids=(),
            idempotent_replay=True,
        )

    # -- helpers ---------------------------------------------------------------

    @staticmethod
    def _require_dm(requester: RequesterVisibility) -> None:
        if requester.role is not RequesterRole.DM:
            raise PromotionError("promotion is DM-only")

    def _ensure_entity(self, command: ApprovePromotionCommand, entity_name: str) -> UUID:
        """Bound-created surfaces mint the owner through the receipted,
        idempotent identity-queue path; a name collision from a partial prior
        attempt falls back to the existing record instead of failing."""
        assert self._entity_creator is not None and command.entity_kind is not None
        try:
            receipt = self._entity_creator.create(
                entity_name,
                command.entity_kind,
                f"{command.idempotency_key}:entity",
            )
            entity_id = getattr(receipt, "entity_id", None)
            if entity_id is None:
                raise PromotionError("entity creation returned no id")
            return entity_id
        except Exception as error:
            if "exists" not in str(error).lower():
                raise
            existing_id = self._reads.entity_id_by_canonical_name(entity_name)
            if existing_id is None:
                raise
            return existing_id

    def _move_linked(
        self, command: ApprovePromotionCommand, entity_id: UUID, entity_name: str
    ) -> tuple[tuple[UUID, ...], tuple[str, ...]]:
        """Re-attribute the linked assertions to the (new) owner. Idempotent:
        a claim that already belongs to the owner counts as moved; other
        failures are collected, never fatal — the assertion stays put."""
        if not command.linked_claim_ids or self._reattribution is None:
            return (), ()
        moved: list[UUID] = []
        errors: list[str] = []
        for claim_id in command.linked_claim_ids:
            try:
                self._reattribution.reattribute(
                    ReattributeClaim(
                        claim_id=claim_id,
                        new_entity_id=entity_id,
                        reason=f"Lore creation: moved to {entity_name}",
                    )
                )
                moved.append(claim_id)
            except ValueError as error:
                if "already belongs" in str(error):
                    moved.append(claim_id)
                else:
                    errors.append(f"{claim_id}: {error}")
        return tuple(moved), tuple(errors)

    def _validated_statements(
        self, command: ApprovePromotionCommand, config: SurfaceConfig
    ) -> tuple[PromotionStatement, ...]:
        if not command.statements:
            return ()
        included_spans: list[tuple[int, int]] = []
        for statement in command.statements:
            if statement.span_end > len(command.document_text):
                raise PromotionError(
                    "the prose changed since review — review the promotion again"
                )
            span_text = command.document_text[
                statement.span_start : statement.span_end
            ].strip()
            if not span_text:
                raise PromotionError(
                    "a reviewed statement no longer matches the prose — "
                    "review the promotion again"
                )
            if statement.state not in config.state_overrides:
                raise PromotionError(
                    f"truth state {statement.state.value} is not offered on this surface"
                )
            if statement.included:
                included_spans.append((statement.span_start, statement.span_end))
        for left, right in included_spans:
            for other_left, other_right in included_spans:
                if (left, right) != (other_left, other_right) and not (
                    right <= other_left or other_right <= left
                ):
                    raise PromotionError("reviewed statements overlap — review again")
        return command.statements

    def _description_command(
        self, command: ApprovePromotionCommand, entity_id: UUID, statements
    ):
        statement_spans = tuple(
            (statement.span_start, statement.span_end)
            for statement in statements
            if statement.included
        )
        return EntityDescriptionCommand(
            entity_id=entity_id,
            text=command.document_text,
            referenced_claim_ids=command.referenced_claim_ids,
            idempotency_key=f"{command.idempotency_key}:file",
            document_id=command.document_id,
            statement_spans=statement_spans,
        )

    def _create_or_revise(
        self,
        command: ApprovePromotionCommand,
        entity_id: UUID,
        included: list[PromotionStatement],
        candidate_ids: tuple[UUID, ...],
        evidence_revision_id: UUID,
    ) -> CandidateProposalVersion:
        items: tuple[ProposalItemDecision, ...] = tuple(
            CreateClaimDecision(
                mutation_kind="create_claim",
                candidate_id=candidate_id,
                evidence_revision_id=evidence_revision_id,
                target_id=uuid4(),
                subject_entity_id=entity_id,
                assertion_text=statement.assertion_text.strip(),
                state=statement.state,
                authority=SURFACE_REGISTRY[command.surface].state_overrides[
                    statement.state
                ],
                visibility=Visibility.DM_ONLY,
                confidence=Decimal("1"),
                is_conditional=False,
                predicts_subject_action=False,
                recorded_at=datetime.now(UTC),
            )
            for statement, candidate_id in zip(
                included, candidate_ids, strict=True
            )
        )
        try:
            return self._proposals.create(
                CreateCandidateProposalCommand(items=items), self._dm()
            )
        except CandidateProposalError as error:
            if "cannot be proposed" not in str(error):
                raise
            # A prior attempt staged these candidates under a pending
            # proposal; converge by revising it to exactly this review.
            existing = self._proposals.get_for_candidate(
                items[0].candidate_id, self._dm()
            )
            if existing is None:
                raise PromotionError(
                    "these statements were already promoted — nothing to commit"
                ) from error
            return self._proposals.revise(
                ReviseCandidateProposalCommand(
                    proposal_id=existing.proposal_id, items=items
                ),
                self._dm(),
            )

    @staticmethod
    def _dm() -> RequesterVisibility:
        return RequesterVisibility(role=RequesterRole.DM)

    def _claim_ids(self, item_ids: tuple[UUID, ...]) -> tuple[UUID, ...]:
        return tuple(
            target_id
            for _item_id, target_id in self._reads.claim_targets_for_items(item_ids)
        )

    def _finish_stored(
        self,
        command: ApprovePromotionCommand,
        entity_id: UUID | None,
        entity_name: str,
        stored: StoredChangeSet,
    ) -> PromotionCommitReceipt:
        if entity_id is None:
            entity_id = self._ensure_entity(command, entity_name)
        file_receipt = self._descriptions.write(
            self._description_command(command, entity_id, ())
        )
        # Apply is safe on a pending set and returns the durable receipt on
        # replay, so a single call finishes either state.
        receipt = self._change_sets.apply(
            ApplyChangeSetCommand(
                change_set_id=stored.change_set_id,
                reviewed_version=stored.reviewed_version,
                approval_id=stored.approval_id,
                content_hash=stored.content_hash,
            )
        )
        claim_ids = self._claim_ids(receipt.applied_item_ids)
        moved_claim_ids, move_errors = self._move_linked(command, entity_id, entity_name)
        return PromotionCommitReceipt(
            entity_id=entity_id,
            entity_name=entity_name,
            document_id=file_receipt.document_id,
            revision_id=file_receipt.revision_id,
            path=file_receipt.path,
            claims_committed=len(claim_ids),
            claim_ids=claim_ids,
            proposal_id=stored.proposal_id,
            change_set_id=stored.change_set_id,
            receipt_id=receipt.receipt_id,
            moved_claim_ids=moved_claim_ids,
            move_errors=move_errors,
            idempotent_replay=True,
        )
