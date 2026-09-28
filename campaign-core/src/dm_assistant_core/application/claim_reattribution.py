"""Assertion re-attribution (TKT-0099).

When Lore creation links an assertion to a new entity, the assertion's
subject changes — the assertion moves from the old owner to the child
entity that it truly belongs to. Provenance is untouched (same source,
same evidence, same text). The old owner gains a "moved to" reference so
the Dossier keeps its tile with a shortcut to the new entity.
"""

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ReattributeClaim(BaseModel):
    model_config = ConfigDict(frozen=True)
    claim_id: UUID
    new_entity_id: UUID
    reason: str = Field(min_length=1, max_length=500)


class ReattributionReceipt(BaseModel):
    model_config = ConfigDict(frozen=True)
    receipt_id: UUID
    claim_id: UUID
    # None on initial attribution (the claim had no owner).
    old_entity_id: UUID | None
    new_entity_id: UUID
    moved_at: datetime


class MovedAssertion(BaseModel):
    """A claim that moved away from this entity — shown on the old owner's
    Dossier as a tile with the assertion text and a shortcut to the new owner."""
    model_config = ConfigDict(frozen=True)
    claim_id: UUID
    assertion_text: str
    state: str
    new_entity_id: UUID
    new_entity_name: str
    moved_at: datetime
    reason: str


class ClaimReattributionRepository(Protocol):
    def claim_subject(self, claim_id: UUID) -> UUID | None: ...
    def claim_exists(self, claim_id: UUID) -> bool: ...

    def move(self, receipt: ReattributionReceipt, reason: str) -> None:
        """Update the claim's subject AND insert the audit row in one transaction."""

    def moved_from(self, entity_id: UUID) -> list[tuple[UUID, str, str, UUID, str, object, str]]:
        """(claim_id, assertion_text, state, new_entity_id, new_entity_name, moved_at, reason)"""


class ClaimReattributionService:
    def __init__(self, repository: ClaimReattributionRepository) -> None:
        self._repository = repository

    def reattribute(self, command: ReattributeClaim) -> ReattributionReceipt:
        # A NULL subject is an orphan awaiting INITIAL attribution (the
        # migration's provenance-first output); a missing claim is an error.
        if not self._repository.claim_exists(command.claim_id):
            raise ValueError("that claim does not exist")
        current = self._repository.claim_subject(command.claim_id)
        if current == command.new_entity_id:
            raise ValueError("the assertion already belongs to that entity")
        receipt = ReattributionReceipt(
            receipt_id=uuid4(),
            claim_id=command.claim_id,
            old_entity_id=current,
            new_entity_id=command.new_entity_id,
            moved_at=datetime.now(UTC),
        )
        self._repository.move(receipt, command.reason)
        return receipt

    def moved_from(self, entity_id: UUID) -> list[MovedAssertion]:
        rows = self._repository.moved_from(entity_id)
        return [
            MovedAssertion(
                claim_id=row[0], assertion_text=row[1], state=row[2],
                new_entity_id=row[3], new_entity_name=row[4],
                moved_at=row[5], reason=row[6],
            )
            for row in rows
        ]
