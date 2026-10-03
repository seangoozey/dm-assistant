"""Controlled record and entity classification values."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class EntityKind(StrEnum):
    NPC = "npc"
    PC = "pc"
    LOCATION = "location"
    FACTION = "faction"
    ITEM = "item"
    EVENT = "event"
    ENCOUNTER = "encounter"
    WORLDBUILDING = "worldbuilding"
    RULES_ELEMENT = "rules_element"


class EntityKindGuidance(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: EntityKind
    label: str
    description: str


ENTITY_KIND_GUIDANCE = (
    EntityKindGuidance(kind=EntityKind.NPC, label="NPC", description="A DM-controlled character."),
    EntityKindGuidance(
        kind=EntityKind.ENCOUNTER,
        label="Encounter",
        description="A table event: an authored encounter that owns its own claims (ADR-0021).",
    ),
    EntityKindGuidance(
        kind=EntityKind.PC,
        label="PC",
        description="A character controlled only by its player.",
    ),
    EntityKindGuidance(
        kind=EntityKind.LOCATION,
        label="Location",
        description="A place at any geographic scale.",
    ),
    EntityKindGuidance(
        kind=EntityKind.FACTION,
        label="Faction",
        description="An organized group with shared identity.",
    ),
    EntityKindGuidance(
        kind=EntityKind.ITEM,
        label="Item",
        description="An in-world object with canonical identity.",
    ),
    EntityKindGuidance(
        kind=EntityKind.EVENT,
        label="Event",
        description="A distinct historical, mythical, or cosmological occurrence.",
    ),
    EntityKindGuidance(
        kind=EntityKind.WORLDBUILDING,
        label="Worldbuilding",
        description="An era, legend, cosmological structure, or abstract setting concept.",
    ),
    EntityKindGuidance(
        kind=EntityKind.RULES_ELEMENT,
        label="Rules element",
        description="A reusable spell, feat, or ability with structured mechanics.",
    ),
)


INITIAL_TAGS = frozenset(
    {
        "history",
        "mythology",
        "cosmology",
        "world",
        "continent",
        "country",
        "region",
        "settlement",
        "monster",
        "deity",
        "religion",
        "political",
    }
)


def normalize_tag(value: str) -> str:
    normalized = " ".join(value.strip().casefold().split())
    if not normalized:
        raise ValueError("tag cannot be empty")
    if len(normalized) > 64:
        raise ValueError("tag cannot exceed 64 characters")
    return normalized


def normalize_tags(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(normalize_tag(value) for value in values)
    if len(set(normalized)) != len(normalized):
        raise ValueError("tags must be unique case-insensitively")
    return normalized
