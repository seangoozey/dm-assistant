"""Structured rules elements and deterministic export profiles.

A rules element is a canonical entity (entity kind ``rules_element``) that represents a
reusable spell, feat, or ability. Its identity is the entity; its kind-specific structured
mechanics live in a separate value object validated against the ``rules_kind``. A versioned
Markdown-card export profile renders a canonical rules element into a deterministic derived
artifact.

This is the v1 foundation (ADR-0005, TKT-0032): a minimal mechanics model and one export
profile. Exhaustive game-system modeling, Foundry export, and in-app schema construction
are out of scope.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

#: The export profile identifier and its current behavior version.
MARKDOWN_CARD_PROFILE = "markdown_card"
MARKDOWN_CARD_PROFILE_VERSION = "markdown-card/1"


class RulesKind(StrEnum):
    """The controlled rules-element subtype under a ``rules_element`` entity."""

    SPELL = "spell"
    FEAT = "feat"
    ABILITY = "ability"


class RulesMechanicsError(ValueError):
    """A rules-element mechanics payload is invalid or does not match its kind."""


class SpellMechanics(BaseModel):
    """Kind-specific structured detail for a spell."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    school: str = Field(min_length=1, max_length=64)
    level: int = Field(ge=0, le=9)
    description: str = Field(min_length=1)


class FeatMechanics(BaseModel):
    """Kind-specific structured detail for a feat or ability."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tier: str = Field(default="general", min_length=1, max_length=64)
    description: str = Field(min_length=1)


class RulesElementMechanics(BaseModel):
    """The structured mechanics for a canonical rules-element entity.

    The ``mechanics`` value is validated against the ``rules_kind`` so an unknown or
    mismatched shape fails fast rather than becoming arbitrary JSON.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    rules_kind: RulesKind
    summary: str = Field(min_length=1, max_length=500)
    mechanics: dict[str, Any]

    @model_validator(mode="after")
    def validate_mechanics_shape(self) -> RulesElementMechanics:
        if self.rules_kind is RulesKind.SPELL:
            SpellMechanics.model_validate(self.mechanics)
        elif self.rules_kind in {RulesKind.FEAT, RulesKind.ABILITY}:
            FeatMechanics.model_validate(self.mechanics)
        return self


def render_markdown_card(
    *,
    canonical_name: str,
    rules_kind: RulesKind,
    summary: str,
    mechanics: dict[str, Any],
) -> str:
    """Render a deterministic Markdown card from a canonical rules element.

    The output is fully determined by its inputs: the same canonical record and profile
    version always produce byte-identical content, so re-export is idempotent on content
    hash.
    """
    kind_label = {"spell": "Spell", "feat": "Feat", "ability": "Ability"}[rules_kind.value]
    lines: list[str] = [f"# {canonical_name}", "", f"**{kind_label}** — {summary}", ""]
    if rules_kind is RulesKind.SPELL:
        spell = SpellMechanics.model_validate(mechanics)
        level_label = "cantrip" if spell.level == 0 else f"level {spell.level}"
        lines.append(f"- **School:** {spell.school}")
        lines.append(f"- **Level:** {level_label}")
        lines.append(f"- **Description:** {spell.description}")
    else:
        feat = FeatMechanics.model_validate(mechanics)
        lines.append(f"- **Tier:** {feat.tier}")
        lines.append(f"- **Description:** {feat.description}")
    lines.append("")
    return "\n".join(lines)
