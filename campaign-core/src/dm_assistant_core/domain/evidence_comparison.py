"""Explicit, conservative comparison inputs; prose alone is not a contradiction proof.

This module is read-only. Its results never authorize canonical mutations.
"""

import hashlib
import json
from enum import StrEnum
from itertools import combinations

from pydantic import BaseModel, ConfigDict, Field

from dm_assistant_core.domain.retrieval import (
    ConflictEvidence,
    RequesterVisibility,
    RetrievalConflict,
    RetrievalQuery,
    RetrievalRecord,
)

POLICY_VERSION = "evidence-comparison-v1"


class ComparisonStatus(StrEnum):
    UNKNOWN = "unknown"
    EQUIVALENT = "equivalent"
    CONFLICT = "conflict"
    POSSIBLE_RETCON = "possible_retcon"


class ComparisonCoordinate(BaseModel):
    """Core-validated enrichment, not a provider-generated triple.

    Scope identifies the same time interval or occurrence. A missing scope cannot
    establish simultaneity. Exclusive must come from a controlled property rule,
    not the mere presence of two different values (e.g. co-founders are possible).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    record_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    property_key: str = Field(min_length=1)
    value_key: str = Field(min_length=1)
    scope_key: str = Field(min_length=1)
    exclusive: bool = False


class ComparisonResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    policy_version: str = POLICY_VERSION
    status: ComparisonStatus = ComparisonStatus.UNKNOWN
    evidence_ids: tuple[str, ...] = ()
    reason: str


def _visible(record: RetrievalRecord, requester: RequesterVisibility) -> bool:
    return (
        requester.role == "dm"
        or record.visibility == "party"
        or (requester.role == "character"
            and record.visibility == f"character:{requester.character_id}")
    )


def compare_evidence(
    left: RetrievalRecord,
    right: RetrievalRecord,
    requester: RequesterVisibility,
    *,
    left_coordinate: ComparisonCoordinate | None = None,
    right_coordinate: ComparisonCoordinate | None = None,
) -> ComparisonResult:
    """Compare only visible, current factual evidence with explicit coordinates.

    Absent/hidden/ineligible comparison evidence shares an opaque unknown result.
    Never expose a hidden ID, reason, count, or conclusion to the requester.
    """
    unknown = ComparisonResult(reason="comparison_not_established")
    for record in (left, right):
        if not _visible(record, requester):
            return unknown
        if (not record.accepted or record.state not in {"observed", "established"}
                or record.authority not in {"real_play", "explicit_lore", "explicit_correction"}
                or record.kind not in {"claim", "relationship"}):
            return unknown
    if left.record_id == right.record_id:
        return unknown
    if left_coordinate is None or right_coordinate is None:
        return unknown
    for record, coordinate in ((left, left_coordinate), (right, right_coordinate)):
        if coordinate.record_id != record.record_id:
            raise ValueError("comparison coordinate must bind to its exact evidence record")
        if record.entity_id is not None and record.entity_id != coordinate.subject_id:
            raise ValueError("comparison coordinate conflicts with the recorded subject")
    if (left_coordinate.subject_id, left_coordinate.property_key, left_coordinate.scope_key) != (
        right_coordinate.subject_id, right_coordinate.property_key, right_coordinate.scope_key
    ):
        return unknown
    ids = tuple(sorted((left.record_id, right.record_id)))
    if left_coordinate.value_key == right_coordinate.value_key:
        # Equality is only of this coordinate, never the complete prose assertions.
        return ComparisonResult(status=ComparisonStatus.EQUIVALENT, evidence_ids=ids,
                                reason="same_scoped_property_value")
    if not (left_coordinate.exclusive and right_coordinate.exclusive):
        return unknown
    states = {left.state, right.state}
    status = (ComparisonStatus.POSSIBLE_RETCON if states == {"observed", "established"}
              else ComparisonStatus.CONFLICT)
    return ComparisonResult(status=status, evidence_ids=ids,
                            reason="different_exclusive_values_in_same_scope")


def _snapshot(record: RetrievalRecord) -> ConflictEvidence:
    return ConflictEvidence.model_validate({
        key: value for key, value in record.model_dump().items()
        if key in ConflictEvidence.model_fields
    })


def _issue_id(payload: dict[str, object]) -> str:
    # Evidence content and comparison scope are included: repairs must revalidate
    # an exact snapshot, not reuse a stale issue after a claim changes.
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return f"comparison:{digest}"


def retrieval_conflicts(
    query: RetrievalQuery,
    records: tuple[RetrievalRecord, ...],
    coordinates: tuple[ComparisonCoordinate, ...],
) -> tuple[tuple[RetrievalConflict, ...], bool]:
    """Expose verified conflicts from trusted internal enrichment, never API input."""
    visible = {record.record_id: record for record in records
               if _visible(record, query.requester_visibility)}
    by_id: dict[str, ComparisonCoordinate] = {}
    for coordinate in coordinates:
        if coordinate.record_id not in visible:
            continue
        if coordinate.record_id in by_id and by_id[coordinate.record_id] != coordinate:
            raise ValueError("ambiguous comparison coordinates for one record")
        by_id[coordinate.record_id] = coordinate
    issues = []
    for left_id, right_id in combinations(sorted(by_id), 2):
        left, right = visible[left_id], visible[right_id]
        lc, rc = by_id[left_id], by_id[right_id]
        result = compare_evidence(left, right, query.requester_visibility,
                                  left_coordinate=lc, right_coordinate=rc)
        if result.status not in {ComparisonStatus.CONFLICT, ComparisonStatus.POSSIBLE_RETCON}:
            continue
        evidence = (_snapshot(left), _snapshot(right))
        payload: dict[str, object] = {
            "version": POLICY_VERSION, "status": result.status.value,
            "evidence": [item.model_dump(mode="json") for item in evidence],
            "coordinates": [lc.model_dump(), rc.model_dump()],
        }
        issues.append(RetrievalConflict(
            issue_id=_issue_id(payload), policy_version=POLICY_VERSION,
            classification=("possible_retcon" if result.status == ComparisonStatus.POSSIBLE_RETCON
                            else "factual_conflict"), verification="verified_comparison",
            reason=result.reason, evidence=evidence, subject_id=lc.subject_id,
            property_key=lc.property_key, scope_key=lc.scope_key,
        ))
        if len(issues) > 50:
            return tuple(issues[:50]), True
    return tuple(issues), False


def legacy_review_issue(records: tuple[RetrievalRecord, ...]) -> tuple[RetrievalConflict, ...]:
    """Compatibility exposure only: a legacy alert cannot assert factual contradiction."""
    snapshots = tuple(_snapshot(record) for record in sorted(records, key=lambda r: r.record_id))
    if len(snapshots) < 2:
        return ()
    payload: dict[str, object] = {
        "version": "legacy-count-review-v1",
        "evidence": [item.model_dump(mode="json") for item in snapshots],
    }
    return (RetrievalConflict(
        issue_id=_issue_id(payload), policy_version="legacy-count-review-v1",
        classification="suspected_conflict", verification="unverified",
        reason="legacy_alert_requires_explicit_comparison", evidence=snapshots,
    ),)
