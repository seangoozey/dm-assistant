"""Controlled vocabularies for template enumerations (TKT-0129).

Template fields (location_type, status, race, sex) draw their offered values
from receipted vocabularies instead of arbitrary free text. Adding or
retiring a value files a receipt; retired values stop being offered but keep
rendering for entries that already carry them. Roles are deliberately NOT a
vocabulary — they are relations between entities and live with membership.
"""

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

# Intrinsic attributes (per the 2026-09-19 classification) with seed values;
# statuses are states — their vocabulary is the assignment machinery, so only
# the offered list lives here.
VOCABULARIES: dict[str, tuple[str, ...]] = {
    "location_type": (
        "region", "city-state", "city", "town", "village", "quarter",
        "building", "castle", "keep", "tower", "monastery", "camp",
        "landmark", "waterway", "road", "wilds", "plane",
    ),
    "status": ("active", "disbanded", "destroyed", "ruined", "hidden", "unknown"),
    "race": ("high elf", "elf", "human", "dwarf", "halfling", "gnome", "half-elf", "orc", "tiefling", "dragonborn"),
    "sex": ("female", "male", "unspecified"),
}


class VocabularyValue(BaseModel):
    model_config = ConfigDict(frozen=True)
    vocabulary: str
    value: str
    retired: bool


class VocabularyChangeReceipt(BaseModel):
    model_config = ConfigDict(frozen=True)
    receipt_id: UUID
    vocabulary: str
    action: str
    value: str
    changed_at: datetime


class VocabularyCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    action: str  # add | retire
    value: str = Field(min_length=1, max_length=80)


class TemplateVocabularyRepository(Protocol):
    def load(self, vocabulary: str) -> dict[str, bool]: ...

    def record(self, receipt: VocabularyChangeReceipt, retired: bool) -> None: ...


class TemplateVocabularyService:
    def __init__(self, repository: TemplateVocabularyRepository) -> None:
        self._repository = repository

    def values(self, vocabulary: str) -> list[VocabularyValue]:
        if vocabulary not in VOCABULARIES:
            raise ValueError(f"unknown template vocabulary '{vocabulary}'")
        stored = self._repository.load(vocabulary)
        merged = {value: False for value in VOCABULARIES[vocabulary]}
        for value, retired in stored.items():
            merged[value] = retired
        return [
            VocabularyValue(vocabulary=vocabulary, value=value, retired=retired)
            for value, retired in sorted(merged.items(), key=lambda item: item[0].casefold())
        ]

    def change(self, vocabulary: str, command: VocabularyCommand) -> VocabularyChangeReceipt:
        if vocabulary not in VOCABULARIES:
            raise ValueError(f"unknown template vocabulary '{vocabulary}'")
        if command.action not in ("add", "retire"):
            raise ValueError("action must be add or retire")
        value = command.value.strip()
        if not value:
            raise ValueError("value must not be blank")
        receipt = VocabularyChangeReceipt(
            receipt_id=uuid4(),
            vocabulary=vocabulary,
            action=command.action,
            value=value,
            changed_at=datetime.now(UTC),
        )
        self._repository.record(receipt, retired=command.action == "retire")
        return receipt
