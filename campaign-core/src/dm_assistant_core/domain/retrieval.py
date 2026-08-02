"""Deterministic grounded-retrieval policy and transport-independent models."""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from dm_assistant_core.domain.models import ClaimState


class AnswerMode(StrEnum):
    ANSWER = "answer"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONFLICT = "conflict"
    POSSIBLE_RETCN = "possible_retcon"
    RESTRICTED = "restricted"


class RequesterRole(StrEnum):
    DM = "dm"
    PARTY = "party"
    CHARACTER = "character"


class RequesterVisibility(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    role: RequesterRole
    character_id: str | None = None

    @model_validator(mode="after")
    def character_requires_identity(self) -> RequesterVisibility:
        if self.role is RequesterRole.CHARACTER and not self.character_id:
            raise ValueError("character requester requires character_id")
        if self.role is not RequesterRole.CHARACTER and self.character_id is not None:
            raise ValueError("character_id is valid only for character requesters")
        return self


class RetrievalRecordKind(StrEnum):
    CLAIM = "claim"
    ALIAS = "alias"
    RELATIONSHIP = "relationship"
    ALIAS_CANDIDATE = "alias_candidate"
    SOURCE_WARNING = "source_warning"
    QUARANTINED_SOURCE = "quarantined_source"
    DERIVED_ARTIFACT = "derived_artifact"


class RetrievalAuthority(StrEnum):
    REAL_PLAY = "real_play"
    EXPLICIT_LORE = "explicit_lore"
    EXPLICIT_CORRECTION = "explicit_correction"
    NPC_INTENTION = "npc_intention"
    PREPARATION = "preparation"
    BRAINSTORM = "brainstorm"
    UNCLASSIFIED = "unclassified"
    DERIVED = "derived"


class RetrievalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    record_id: str = Field(min_length=1)
    kind: RetrievalRecordKind
    assertion: str = Field(min_length=1)
    state: ClaimState
    authority: RetrievalAuthority
    visibility: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    citation: str = Field(min_length=1)
    accepted: bool
    recorded_at: str | None = None
    effective_from: str | None = None
    expected_at: str | None = None
    observed_at: str | None = None


class RetrievalQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    question: str = Field(min_length=1)
    requester_visibility: RequesterVisibility


class EvidenceRole(StrEnum):
    SUPPORT = "support"
    CONTEXT = "context"
    CONFLICT = "conflict"


class RetrievedEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    record_id: str
    assertion: str
    citation: str
    state: ClaimState
    authority: RetrievalAuthority
    role: EvidenceRole


class RetrievalReason(StrEnum):
    GROUNDED_ANSWER = "grounded_answer"
    UNSUPPORTED_DETAIL = "unsupported_detail"
    NONCANON_ONLY = "noncanon_only"
    VISIBILITY_RESTRICTED = "visibility_restricted"
    CONFLICTING_AUTHORITY = "conflicting_authority"
    POSSIBLE_RETCN = "possible_retcon"


class RetrievalResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    answer_mode: AnswerMode
    evidence: tuple[RetrievedEvidence, ...]
    citations: tuple[str, ...]
    reasons: tuple[RetrievalReason, ...] = Field(min_length=1)


class RetrievalPolicy:
    """Apply visibility, authority, conflict, and sufficiency rules to relevant records."""

    def evaluate(
        self,
        query: RetrievalQuery,
        records: tuple[RetrievalRecord, ...],
    ) -> RetrievalResult:
        visible = tuple(record for record in records if _is_visible(record, query))
        hidden_authoritative = tuple(
            record
            for record in records
            if record not in visible and _is_authoritative(record)
        )
        authoritative = tuple(record for record in visible if _is_authoritative(record))
        context = tuple(record for record in visible if not _is_authoritative(record))

        if hidden_authoritative:
            mode = AnswerMode.RESTRICTED
            reasons = (RetrievalReason.VISIBILITY_RESTRICTED,)
        else:
            conflict_mode = _conflict_mode(query, authoritative, context)
            if conflict_mode is not None:
                mode = conflict_mode
                reasons = (
                    RetrievalReason.POSSIBLE_RETCN
                    if mode is AnswerMode.POSSIBLE_RETCN
                    else RetrievalReason.CONFLICTING_AUTHORITY,
                )
            elif not authoritative:
                mode = AnswerMode.INSUFFICIENT_EVIDENCE
                reasons = (
                    RetrievalReason.NONCANON_ONLY
                    if context
                    else RetrievalReason.UNSUPPORTED_DETAIL,
                )
            elif not _authoritative_suffices(query, authoritative):
                mode = AnswerMode.INSUFFICIENT_EVIDENCE
                reasons = (RetrievalReason.UNSUPPORTED_DETAIL,)
            else:
                mode = AnswerMode.ANSWER
                reasons = (RetrievalReason.GROUNDED_ANSWER,)

        selected = _select_evidence(query, mode, authoritative, context)
        role = (
            EvidenceRole.CONFLICT
            if mode in {AnswerMode.CONFLICT, AnswerMode.POSSIBLE_RETCN}
            else EvidenceRole.SUPPORT
        )
        evidence: list[RetrievedEvidence] = []
        authoritative_ids = {record.record_id for record in authoritative}
        for record in sorted(selected, key=lambda item: (item.citation, item.record_id)):
            record_role = role if record.record_id in authoritative_ids else EvidenceRole.CONTEXT
            if mode is AnswerMode.INSUFFICIENT_EVIDENCE:
                record_role = EvidenceRole.CONTEXT
            evidence.append(
                RetrievedEvidence(
                    record_id=record.record_id,
                    assertion=record.assertion,
                    citation=record.citation,
                    state=record.state,
                    authority=record.authority,
                    role=record_role,
                )
            )
        citations = tuple(sorted({item.citation for item in evidence}))
        return RetrievalResult(
            answer_mode=mode,
            evidence=tuple(evidence),
            citations=citations,
            reasons=reasons,
        )


def _is_visible(record: RetrievalRecord, query: RetrievalQuery) -> bool:
    requester = query.requester_visibility
    if requester.role is RequesterRole.DM:
        return True
    if record.visibility == "party":
        return True
    return bool(
        requester.role is RequesterRole.CHARACTER
        and record.visibility == f"character:{requester.character_id}"
    )


def _is_authoritative(record: RetrievalRecord) -> bool:
    return bool(
        record.accepted
        and record.kind
        in {
            RetrievalRecordKind.CLAIM,
            RetrievalRecordKind.ALIAS,
            RetrievalRecordKind.RELATIONSHIP,
        }
        and record.state in {ClaimState.OBSERVED, ClaimState.ESTABLISHED, ClaimState.INTENDED}
        and record.authority
        in {
            RetrievalAuthority.REAL_PLAY,
            RetrievalAuthority.EXPLICIT_LORE,
            RetrievalAuthority.EXPLICIT_CORRECTION,
            RetrievalAuthority.NPC_INTENTION,
        }
    )


def _conflict_mode(
    query: RetrievalQuery,
    authoritative: tuple[RetrievalRecord, ...],
    context: tuple[RetrievalRecord, ...],
) -> AnswerMode | None:
    claims = [record for record in authoritative if record.kind is RetrievalRecordKind.CLAIM]
    if len(claims) >= 2:
        states = {record.state for record in claims}
        if ClaimState.OBSERVED in states and ClaimState.ESTABLISHED in states:
            return AnswerMode.POSSIBLE_RETCN
        if states == {ClaimState.ESTABLISHED}:
            return AnswerMode.CONFLICT
    disputed_aliases = [
        record
        for record in context
        if record.kind is RetrievalRecordKind.ALIAS_CANDIDATE
        and record.state is ClaimState.DISPUTED
    ]
    if len(disputed_aliases) >= 2 and query.question.casefold().startswith("did "):
        return AnswerMode.CONFLICT
    return None


def _authoritative_suffices(
    query: RetrievalQuery,
    authoritative: tuple[RetrievalRecord, ...],
) -> bool:
    question = query.question.casefold().strip()
    combined = " ".join(record.assertion.casefold() for record in authoritative)
    if question.startswith("how many"):
        return bool(
            re.search(
                r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b",
                combined,
            )
        )
    if question.startswith("when "):
        return any(
            record.observed_at or record.effective_from or record.expected_at
            for record in authoritative
        ) or bool(re.search(r"\b(?:day|date|year|founded|occurred)\b", combined))
    if " also called " in question:
        requested_alias = question.split(" also called ", maxsplit=1)[1].rstrip(" ?")
        return any(
            record.kind is RetrievalRecordKind.ALIAS
            and requested_alias in record.assertion.casefold()
            for record in authoritative
        )
    if "names of" in question:
        return "name" in combined and bool(_tokens(question) & _tokens(combined))
    return True


def _select_evidence(
    query: RetrievalQuery,
    mode: AnswerMode,
    authoritative: tuple[RetrievalRecord, ...],
    context: tuple[RetrievalRecord, ...],
) -> tuple[RetrievalRecord, ...]:
    if mode in {AnswerMode.CONFLICT, AnswerMode.POSSIBLE_RETCN}:
        return (*authoritative, *context)
    if mode is AnswerMode.RESTRICTED:
        return authoritative
    if mode is AnswerMode.INSUFFICIENT_EVIDENCE:
        return (*authoritative, *context)
    selected_context: tuple[RetrievalRecord, ...] = ()
    if any(
        record.authority is RetrievalAuthority.EXPLICIT_CORRECTION
        for record in authoritative
    ):
        selected_context = tuple(
            record for record in context if record.state is ClaimState.SUPERSEDED
        )
    elif query.question.casefold().strip().startswith("when ") and any(
        record.state is ClaimState.OBSERVED for record in authoritative
    ):
        selected_context = tuple(record for record in context if record.expected_at)
    return (*authoritative, *selected_context)


STOP_WORDS = {
    "a",
    "also",
    "an",
    "and",
    "are",
    "at",
    "did",
    "do",
    "does",
    "have",
    "how",
    "is",
    "it",
    "known",
    "of",
    "on",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
}


def _tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for raw in re.findall(r"[a-z0-9]+", text.casefold()):
        if raw in STOP_WORDS:
            continue
        tokens.add(raw[:-1] if len(raw) > 3 and raw.endswith("s") else raw)
    return tokens
