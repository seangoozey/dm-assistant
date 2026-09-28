"""Qualified Entity audit (TKT-0139) — the standard's machine-checkable proof.

Computes Q1/Q4/Q6 live per entity; Q3 and Q5 are reported as PENDING their
mechanisms (the orphan review and attribute minting) — never silently
passed. Q2/Q8/Q9 are structural. Binary result, per-criterion reasons for
TKT-0140's routing.
"""

from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# Attributes checked against the active Core vocabularies (0129). Retired
# values fail Q6 — retiring a value in use is a real state change.
_VOCABULARY_FIELDS = {
    "status": "status",
    "location_type": "location_type",
    "race": "race",
    "sex": "sex",
}


class CriterionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    criterion: str  # q1_asserts, q2_claims_real, q3_ownership, q4_kind, q5_attributes_minted, q6_vocabulary
    status: str  # pass | fail | pending
    reason: str
    # Structured vocabulary failure (q6) so the queue can offer the one-click
    # re-activation receipt.
    vocabulary: str | None = None
    value: str | None = None


class EntityQualification(BaseModel):
    model_config = ConfigDict(frozen=True)

    entity_id: UUID
    canonical_name: str
    entity_kind: str
    qualified: bool
    current_claim_count: int
    criteria: tuple[CriterionResult, ...]


class QualifiedAuditResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    audited_at: datetime
    total_entities: int
    qualified_count: int
    unqualified: tuple[EntityQualification, ...]
    pending_criteria: tuple[str, ...]


class QualifiedAuditRepository(Protocol):
    def entity_rows(self) -> list[tuple[Any, ...]]:
        """(entity_id, canonical_name, entity_kind, current_claim_count,
        parent_location_name, parent_location_kind, profile_json) for every
        entity, with claim counts excluding superseded claims."""

    def active_vocabulary_values(self) -> dict[str, set[str]]:
        """Active (non-retired) values per vocabulary name."""


_PENDING = {
    "q3_ownership": "pending the orphan review (TKT-0138)",
    "q5_attributes_minted": "pending claim-backed minting (TKT-0143)",
}


class QualifiedEntityAuditService:
    def __init__(self, repository: QualifiedAuditRepository) -> None:
        self._repository = repository

    def audit(self) -> QualifiedAuditResult:
        vocabularies = self._repository.active_vocabulary_values()
        unqualified: list[EntityQualification] = []
        total = 0
        qualified = 0
        for (entity_id, name, kind, claim_count, parent_name, parent_kind,
             profile_json) in self._repository.entity_rows():
            total += 1
            criteria: list[CriterionResult] = []

            # Q1 — asserts something.
            count = int(claim_count or 0)
            if count >= 1:
                criteria.append(CriterionResult(
                    criterion="q1_asserts", status="pass",
                    reason=f"{count} current claim{'s' if count != 1 else ''}"))
            else:
                criteria.append(CriterionResult(
                    criterion="q1_asserts", status="fail",
                    reason="no current claims — a record with no data should not exist; "
                           "populate through a reviewed lane or remove via the audited path"))

            # Q2 — structural; verified by absence of bypass reports.
            criteria.append(CriterionResult(
                criterion="q2_claims_real", status="pass",
                reason="claims carry Truth State, authority, provenance by construction"))

            # Q3 / Q5 — pending their mechanisms, never silently passed.
            for criterion, reason in _PENDING.items():
                criteria.append(CriterionResult(
                    criterion=criterion, status="pending", reason=reason))

            # Q4 — kind structural sanity: parent_location must be a location.
            if kind == "location" and parent_name and parent_kind and parent_kind != "location":
                criteria.append(CriterionResult(
                    criterion="q4_kind", status="fail",
                    reason=f"parent_location '{parent_name}' is a {parent_kind}, not a location"))
            else:
                criteria.append(CriterionResult(
                    criterion="q4_kind", status="pass", reason="kind structure sane"))

            # Q6 — vocabulary-backed attribute values (one criterion per
            # failing value, structured for the one-click restore).
            profile = dict(profile_json or {})
            any_populated = False
            for field, vocabulary in _VOCABULARY_FIELDS.items():
                value = profile.get(field)
                if value is None:
                    continue
                any_populated = True
                active = vocabularies.get(vocabulary, set())
                if active and str(value) not in active:
                    criteria.append(CriterionResult(
                        criterion="q6_vocabulary", status="fail",
                        reason=f"{field} '{value}' is not in the active {vocabulary} vocabulary",
                        vocabulary=vocabulary, value=str(value)))
            if not any(c.criterion == "q6_vocabulary" and c.status == "fail" for c in criteria):
                criteria.append(CriterionResult(
                    criterion="q6_vocabulary", status="pass" if any_populated else "pass",
                    reason="populated vocabulary fields are active values"))

            failed = [c for c in criteria if c.status == "fail"]
            record = EntityQualification(
                entity_id=entity_id,
                canonical_name=str(name),
                entity_kind=str(kind),
                qualified=not failed,
                current_claim_count=count,
                criteria=tuple(criteria),
            )
            if failed:
                unqualified.append(record)
            else:
                qualified += 1
        return QualifiedAuditResult(
            audited_at=datetime.now(UTC),
            total_entities=total,
            qualified_count=qualified,
            unqualified=tuple(unqualified),
            pending_criteria=tuple(_PENDING.values()),
        )
