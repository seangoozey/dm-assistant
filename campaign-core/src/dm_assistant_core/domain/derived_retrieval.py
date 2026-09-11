"""Read-only safety boundary for derived-index suggestions; not an answer engine.

Callers supply current Core records, not copies supplied by an index. This boundary
does not authorize graph traversal; only independently authorized direct suggestions
may enter until the shared projection provides validated paths.
"""

import hashlib

from pydantic import BaseModel, ConfigDict, Field

from dm_assistant_core.domain.evidence_comparison import ComparisonCoordinate, retrieval_conflicts
from dm_assistant_core.domain.retrieval import (
    AnswerMode,
    EvidenceRole,
    RetrievalQuery,
    RetrievalReason,
    RetrievalRecord,
    RetrievalResult,
    RetrievedEvidence,
    _is_visible,
)


def record_fingerprint(record: RetrievalRecord) -> str:
    """Bind all retrieval-visible fields, including evidence, state and visibility."""
    return hashlib.sha256(record.model_dump_json().encode()).hexdigest()


class IndexSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    record_id: str = Field(min_length=1)
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


def evaluate_suggestions(
    query: RetrievalQuery,
    suggestions: tuple[IndexSuggestion, ...],
    current_records: tuple[RetrievalRecord, ...],
    *,
    comparison_coordinates: tuple[ComparisonCoordinate, ...] = (),
) -> RetrievalResult:
    """Revalidate IDs and snapshots, preserve context, and expose verified issues.

No rejection reasons/counts reveal whether an ID was hidden, stale or absent.
Similarity, shared entities and claim counts never establish answer sufficiency.
"""
    if len(suggestions) > 100:
        raise ValueError("at most 100 direct suggestions allowed")
    eligible = {
        record.record_id: record for record in current_records
        if _is_visible(record, query) and record.state not in {"superseded", "rejected"}
        and record.kind in {"claim", "relationship", "alias"}
        and (not query.entity_kinds or record.entity_kind in query.entity_kinds)
        and (not query.tags or set(query.tags).issubset(record.tags))
    }
    selected = {}
    for suggestion in suggestions:
        record = eligible.get(suggestion.record_id)
        if record is not None and suggestion.fingerprint == record_fingerprint(record):
            selected[record.record_id] = record
    records = tuple(selected.values())
    conflicts, truncated = retrieval_conflicts(query, records, comparison_coordinates)
    verified_ids = {item.record_id for issue in conflicts for item in issue.evidence}
    mode = AnswerMode.INSUFFICIENT_EVIDENCE
    reason = RetrievalReason.UNSUPPORTED_DETAIL
    if conflicts:
        retcon = any(issue.classification == "possible_retcon" for issue in conflicts)
        mode = AnswerMode.POSSIBLE_RETCN if retcon else AnswerMode.CONFLICT
        reason = RetrievalReason.POSSIBLE_RETCN if retcon else RetrievalReason.CONFLICTING_AUTHORITY
    evidence = tuple(RetrievedEvidence(
        record_id=r.record_id, assertion=r.assertion, citation=r.citation,
        state=r.state, authority=r.authority, entity_id=r.entity_id,
        role=EvidenceRole.CONFLICT if r.record_id in verified_ids else EvidenceRole.CONTEXT,
    ) for r in records)
    return RetrievalResult(answer_mode=mode, evidence=evidence,
                           citations=tuple(sorted({r.citation for r in records})),
                           reasons=(reason,),
                           conflicts=conflicts, conflicts_truncated=truncated)
