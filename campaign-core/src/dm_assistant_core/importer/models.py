"""Typed records exchanged between the read-only connector and Campaign Core."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from dm_assistant_core.domain import ClaimState, Visibility

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$", strict=True)]


class ImportClassification(StrEnum):
    DURABLE_EVIDENCE = "durable_evidence"
    REAL_PLAY_EVIDENCE = "real_play_evidence"
    NONCANON_EVIDENCE = "noncanon_evidence"
    PLANNING_EVIDENCE = "planning_evidence"
    PLANNED_PREPARATION = "planned_preparation"
    PREPARATION = "preparation"
    CANONICAL_ARTIFACT = "canonical_artifact"
    TEMPLATE = "template"
    NAVIGATION_INDEX = "navigation_index"
    QUARANTINE = "quarantine"


class ImportOutcome(StrEnum):
    NEW = "new"
    UNCHANGED = "unchanged"
    CHANGED = "changed"
    REEXTRACTED = "reextracted"
    MOVED = "moved"
    POSSIBLE_MOVE = "possible_move"
    MISSING_SOURCE = "missing_source"
    TEMPLATE_EXCLUDED = "template_excluded"
    NAVIGATION_EXCLUDED = "navigation_excluded"
    QUARANTINED = "quarantined"
    REVIEW_REQUIRED = "review_required"
    FAILED = "failed"


class ImportWarning(StrEnum):
    UNRESOLVED_LINK = "unresolved_link"
    UNRESOLVED_LINK_DIAGNOSTIC_ONLY = "unresolved_link_diagnostic_only"
    UNRESOLVED_CANON_DELTAS = "unresolved_canon_deltas"
    APPLIED_DELTA_NO_REAPPLY = "applied_delta_no_reapply"
    LEGACY_SESSION_METADATA = "legacy_session_metadata"
    LEGACY_SESSION_WRONG_PATH = "legacy_session_wrong_path"
    PROMOTION_RECEIPT_NO_REAPPLY = "promotion_receipt_no_reapply"
    MISSING_FRONTMATTER = "missing_frontmatter"
    INVALID_FRONTMATTER = "invalid_frontmatter"
    READ_ALOUD_IS_DERIVED = "read_aloud_is_derived"
    UNKNOWN_FORMAT = "unknown_format"
    INVALID_UTF8 = "invalid_utf8"
    CLASSIFICATION_CONFLICT = "classification_conflict"
    POSSIBLE_MOVE_REVIEW = "possible_move_review"


class CandidateAuthority(StrEnum):
    REAL_PLAY = "real_play"
    EXPLICIT_LORE = "explicit_lore"
    NPC_INTENTION = "npc_intention"
    PREPARATION = "preparation"
    BRAINSTORM = "brainstorm"
    UNCLASSIFIED = "unclassified"


class ImportCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fingerprint: Sha256
    section: NonEmptyText
    assertion_text: NonEmptyText
    state: ClaimState
    authority: CandidateAuthority
    visibility: Visibility = Visibility.DM_ONLY
    conditional: bool = False
    predicts_pc_action: bool = False
    evidence_only: bool = False
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    extractor_version: NonEmptyText


class ScannedSource(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        ser_json_bytes="base64",
        val_json_bytes="base64",
    )

    path: NonEmptyText
    content_hash: Sha256
    content: bytes
    filesystem_modified_at: datetime
    external_id: str | None = None
    canonical_name: str | None = None
    frontmatter: dict[str, Any]
    classification: ImportClassification
    proposed_outcome: ImportOutcome
    candidates: tuple[ImportCandidate, ...]
    entity_candidates: int = Field(ge=0)
    warnings: tuple[ImportWarning, ...]


class MarkdownScanBatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    root_identifier: NonEmptyText
    snapshot_at: datetime
    importer_version: NonEmptyText
    parser_version: NonEmptyText
    path_policy_version: NonEmptyText
    idempotency_key: NonEmptyText
    reextract_paths: tuple[str, ...] = ()
    excluded_paths_encountered: tuple[str, ...]
    files: tuple[ScannedSource, ...]


class ImportFileOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: NonEmptyText
    outcome: ImportOutcome
    content_hash: Sha256 | None = None
    source_document_id: UUID | None = None
    source_revision_id: UUID | None = None
    candidate_ids: tuple[UUID, ...] = ()
    review_ids: tuple[UUID, ...] = ()
    canonical_change_set_ids: tuple[UUID, ...] = ()
    warnings: tuple[ImportWarning, ...] = ()


class ImportObservationReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    admitted_file_count: int = Field(ge=0)
    excluded_paths_encountered: tuple[str, ...]
    files: tuple[ImportFileOutcome, ...]


class ImportReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    import_run_id: UUID
    idempotency_key: NonEmptyText
    root_identifier: NonEmptyText
    snapshot_at: datetime
    importer_version: NonEmptyText
    parser_version: NonEmptyText
    path_policy_version: NonEmptyText
    outcome: NonEmptyText
    observation: ImportObservationReceipt
    idempotent_replay: bool


class ImportRejectedError(ValueError):
    """The submitted scan failed integrity or reconciliation validation."""
