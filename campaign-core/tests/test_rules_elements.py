from __future__ import annotations

import pytest
from pydantic import ValidationError

from dm_assistant_core.domain.rules_elements import (
    MARKDOWN_CARD_PROFILE,
    MARKDOWN_CARD_PROFILE_VERSION,
    RulesElementMechanics,
    RulesKind,
    SpellMechanics,
    render_markdown_card,
)


class TestRulesKind:
    def test_spell_feat_ability_are_the_only_kinds(self) -> None:
        assert {RulesKind.SPELL, RulesKind.FEAT, RulesKind.ABILITY} == set(RulesKind)


class TestRulesElementMechanics:
    def test_valid_spell_mechanics(self) -> None:
        mechanics = RulesElementMechanics(
            rules_kind=RulesKind.SPELL,
            summary="A bolt of arcane force.",
            mechanics={"school": "Evocation", "level": 3, "description": "Strikes a target."},
        )
        assert mechanics.rules_kind is RulesKind.SPELL

    def test_valid_feat_mechanics(self) -> None:
        mechanics = RulesElementMechanics(
            rules_kind=RulesKind.FEAT,
            summary="Spend Hit Dice for spell damage.",
            mechanics={"tier": "mantle", "description": "Up to 3 Hit Dice add damage."},
        )
        assert mechanics.rules_kind is RulesKind.FEAT

    def test_valid_ability_mechanics(self) -> None:
        mechanics = RulesElementMechanics(
            rules_kind=RulesKind.ABILITY,
            summary="A reactive counter.",
            mechanics={"description": "React to an incoming attack."},
        )
        assert mechanics.rules_kind is RulesKind.ABILITY

    def test_spell_mechanics_with_feat_kind_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RulesElementMechanics(
                rules_kind=RulesKind.FEAT,
                summary="x",
                mechanics={"school": "Evocation", "level": 1, "description": "y"},
            )

    def test_unknown_mechanics_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RulesElementMechanics(
                rules_kind=RulesKind.SPELL,
                summary="x",
                mechanics={"school": "Evocation", "level": 1, "description": "y", "junk": True},
            )

    def test_spell_level_bounds(self) -> None:
        with pytest.raises(ValidationError):
            SpellMechanics(school="Evocation", level=10, description="x")
        with pytest.raises(ValidationError):
            SpellMechanics(school="Evocation", level=-1, description="x")

    def test_cantrip_level_zero(self) -> None:
        spell = SpellMechanics(school="Transmutation", level=0, description="A minor effect.")
        assert spell.level == 0

    def test_empty_summary_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RulesElementMechanics(
                rules_kind=RulesKind.SPELL,
                summary="",
                mechanics={"school": "Evocation", "level": 1, "description": "y"},
            )

    def test_extra_top_level_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RulesElementMechanics(
                rules_kind=RulesKind.SPELL,
                summary="x",
                mechanics={"school": "Evocation", "level": 1, "description": "y"},
                junk=True,  # type: ignore[call-arg]
            )


class TestMarkdownCardProfile:
    def test_spell_card_is_deterministic(self) -> None:
        args = {
            "canonical_name": "Force Bolt",
            "rules_kind": RulesKind.SPELL,
            "summary": "A bolt of arcane force.",
            "mechanics": {"school": "Evocation", "level": 1, "description": "Strikes the target."},
        }
        assert render_markdown_card(**args) == render_markdown_card(**args)

    def test_spell_card_content(self) -> None:
        card = render_markdown_card(
            canonical_name="Force Bolt",
            rules_kind=RulesKind.SPELL,
            summary="A bolt of arcane force.",
            mechanics={"school": "Evocation", "level": 1, "description": "Strikes the target."},
        )
        assert "# Force Bolt" in card
        assert "**Spell**" in card
        assert "Evocation" in card
        assert "level 1" in card

    def test_cantrip_renders_cantrip_not_level_zero(self) -> None:
        card = render_markdown_card(
            canonical_name="Spark",
            rules_kind=RulesKind.SPELL,
            summary="A tiny flame.",
            mechanics={"school": "Evocation", "level": 0, "description": "Lights a candle."},
        )
        assert "cantrip" in card
        assert "level 0" not in card

    def test_feat_card_content(self) -> None:
        card = render_markdown_card(
            canonical_name="Raw Flow",
            rules_kind=RulesKind.FEAT,
            summary="Spend Hit Dice for spell damage.",
            mechanics={"tier": "mantle", "description": "Up to 3 Hit Dice add damage."},
        )
        assert "# Raw Flow" in card
        assert "**Feat**" in card
        assert "mantle" in card

    def test_ability_card_uses_general_tier_by_default(self) -> None:
        card = render_markdown_card(
            canonical_name="Counter Strike",
            rules_kind=RulesKind.ABILITY,
            summary="A reactive counter.",
            mechanics={"description": "React to an incoming attack."},
        )
        assert "**Ability**" in card
        assert "general" in card

    def test_different_inputs_produce_different_cards(self) -> None:
        card_a = render_markdown_card(
            canonical_name="Force Bolt",
            rules_kind=RulesKind.SPELL,
            summary="A bolt.",
            mechanics={"school": "Evocation", "level": 1, "description": "x"},
        )
        card_b = render_markdown_card(
            canonical_name="Force Bolt",
            rules_kind=RulesKind.SPELL,
            summary="A bolt.",
            mechanics={"school": "Abjuration", "level": 1, "description": "x"},
        )
        assert card_a != card_b

    def test_profile_version_is_stable(self) -> None:
        assert MARKDOWN_CARD_PROFILE == "markdown_card"
        assert MARKDOWN_CARD_PROFILE_VERSION == "markdown-card/1"
