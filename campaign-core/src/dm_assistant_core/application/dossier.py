"""DM-curated dossier promotion (TKT-0121).

Which established claims earn a Dossier card is the DM's editorial act, not a
template heuristic: promote/demote is a receipted per-claim decision, the
latest decision per claim wins, and the entry's dossier is exactly the set of
promoted claims still current (superseded claims drop out until their
successor is promoted).
"""

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict


class DossierDecisionReceipt(BaseModel):
    model_config = ConfigDict(frozen=True)
    receipt_id: UUID
    entity_id: UUID
    claim_id: UUID
    action: str
    decided_at: datetime


class DossierView(BaseModel):
    model_config = ConfigDict(frozen=True)
    entity_id: UUID
    promoted_claim_ids: tuple[UUID, ...]


class DossierRepository(Protocol):
    def latest_by_claim(self, entity_id: UUID) -> dict[UUID, str]: ...

    def record(self, receipt: DossierDecisionReceipt) -> None: ...


class DossierService:
    def __init__(self, repository: DossierRepository) -> None:
        self._repository = repository

    def view(self, entity_id: UUID) -> DossierView:
        promoted = tuple(
            claim_id
            for claim_id, action in sorted(
                self._repository.latest_by_claim(entity_id).items(),
                key=lambda item: str(item[0]),
            )
            if action == "promote"
        )
        return DossierView(entity_id=entity_id, promoted_claim_ids=promoted)

    def promote(self, entity_id: UUID, claim_id: UUID) -> DossierDecisionReceipt:
        return self._decide(entity_id, claim_id, "promote")

    def demote(self, entity_id: UUID, claim_id: UUID) -> DossierDecisionReceipt:
        return self._decide(entity_id, claim_id, "demote")

    def _decide(self, entity_id: UUID, claim_id: UUID, action: str) -> DossierDecisionReceipt:
        receipt = DossierDecisionReceipt(
            receipt_id=uuid4(),
            entity_id=entity_id,
            claim_id=claim_id,
            action=action,
            decided_at=datetime.now(UTC),
        )
        self._repository.record(receipt)
        return receipt
