from uuid import uuid4

from dm_assistant_core.application.identity_gaps import (
    IdentityGap,
    mine_gaps,
    normalize_surface,
    related_surfaces,
    role_hint_surfaces,
)


def claims(*texts):
    return [(uuid4(), text) for text in texts]


def test_recurring_phrase_surfaces_with_display_casing_and_evidence():
    result = mine_gaps(claims(
        "At midnight the Court of the Stars convenes.",
        "Members keep vigil within the Court of the Stars tonight.",
        "Unrelated prose about lamps.",
    ), known=set())
    gap = next(g for g in result if g.normalized_surface == "court of the stars")
    assert gap.surface == "Court of the Stars"
    assert gap.claims_with_phrase == 2
    assert gap.total_mentions == 2
    assert len(gap.evidence) == 2
    assert "Court of the Stars" in gap.evidence[0].excerpt


def test_sentence_initial_article_strips_from_the_surface_key():
    result = mine_gaps(claims(
        "The Court of the Stars convenes at midnight.",
        "They wait inside the Court of the Stars.",
    ), known=set())
    assert "court of the stars" in {g.normalized_surface for g in result}


def test_known_canonical_names_and_aliases_never_surface():
    result = mine_gaps(claims(
        "Romulus rules from the castle. Romulus writes.",
        "The Shadow answers. The Shadow watches.",
    ), known={"romulus", "the shadow"})
    assert result == []


def test_single_claim_phrases_do_not_qualify():
    result = mine_gaps(claims("The Lonely Beacon shines once."), known=set())
    assert result == []


def test_sentence_start_noise_is_suppressed_by_lowercase_frequency():
    texts = [f"note {i}: this lamp is lit" for i in range(12)]
    texts.append("This Particular Phrase appears once capitalized.")
    texts.append("This Particular Phrase appears again capitalized.")
    result = mine_gaps(claims(*texts), known=set())
    surfaces = {g.normalized_surface for g in result}
    assert "this" not in surfaces
    assert "this particular phrase" in surfaces


def test_normalize_surface_is_stable():
    assert normalize_surface("  The   Grand Inquisitor ") == "grand inquisitor"
    assert normalize_surface("Court of the Stars the") == "court of the stars"


def _gap(surface: str) -> IdentityGap:
    normalized = normalize_surface(surface)
    return IdentityGap(surface=surface, normalized_surface=normalized,
                       claims_with_phrase=2, total_mentions=2)


def test_related_surfaces_present_variants_without_merging():
    gaps = [_gap("Court of the Stars"), _gap("the Stars"), _gap("Silver Cloaks"), _gap("White Cloaks"),
            _gap("Church of Malygos"), _gap("Cult of Malygos")]
    related = related_surfaces(gaps)
    assert related["court of the stars"] == ("the Stars",)
    assert related["stars"] == ("Court of the Stars",)
    # Sharing a proper head noun relates them — and keeps them separate decisions.
    assert related["church of malygos"] == ("Cult of Malygos",)
    # Sharing a generic organizational noun does not relate different orders.
    assert "silver cloaks" not in related
    assert "white cloaks" not in related


def test_role_hint_surfaces_collect_final_content_words():
    finals = role_hint_surfaces(["Grand Inquisitor", "The Shadow King"])
    assert finals == {"inquisitor", "king"}
    assert role_hint_surfaces(["the"]) == set()
