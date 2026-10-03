"""The orphaned-claims review (TKT-0138): claims with no owning record.

Incomplete migration left ~186 non-superseded claims whose subject was never
assigned — provenance-first import output. They are invisible today: no
surface lists them (audit Q3 reports pending). This service produces THE
list — each orphan with its evidence and DETERMINISTIC suggested owners —
so the DM can finally see the population before the assignment actions land.

Suggestions are never authoritative: co-mention links (the importer's
word-boundary linking and direct-capture mentions, already in
``claim_related_entities``) outrank raw name-in-text matches, and longer
names outrank shorter ones (more specific). No AI participates in v1 — the
AI owner-suggestion seam (0137 seam 4) is a later, wand-marked addition.
"""

import re
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from dm_assistant_core.application.exclusive_claims import _normalize_name

from dm_assistant_core.application.owner_suggestions import (
    name_pattern as _name_pattern,
    suggest_owner_matches,
)

_MAX_SUGGESTIONS = 3
_MAX_SOURCE_PATHS = 3


class OrphanOwnerSuggestion(BaseModel):
    model_config = ConfigDict(frozen=True)

    entity_id: UUID
    entity_name: str
    entity_kind: str
    basis: str  # "co-mention" | "name in text"


class OrphanedClaim(BaseModel):
    model_config = ConfigDict(frozen=True)

    claim_id: UUID
    assertion_text: str
    state: str
    authority: str
    recorded_at: str | None = None
    source_paths: tuple[str, ...] = ()
    # The entity the claim's evidence document is attached to (the 2026-09-30
    # default disposition), when a match exists. Sessions never match
    # (session notes are not entity documents).
    document_owner_id: UUID | None = None
    document_owner_name: str | None = None
    suggestions: tuple[OrphanOwnerSuggestion, ...] = ()


class EncounterGroup(BaseModel):
    """One encounter's orphaned material, ready to mint (TKT-0138's
    encounter slice / ADR-0021): mint the encounter entity, then its claims
    assign to it in the same reviewed action."""

    model_config = ConfigDict(frozen=True)

    name: str
    claim_ids: tuple[UUID, ...]
    document_paths: tuple[str, ...]
    # False when the derived name already resolves to an existing identity
    # (apostrophe/case-insensitive — "Ishirala" collides with "Ishi'ra'la"):
    # the DM edits the name before minting; the mint itself still refuses.
    name_available: bool = True


class OrphanedClaimsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_claims: int
    claims_with_suggestions: int
    claims: tuple[OrphanedClaim, ...]
    encounter_groups: tuple[EncounterGroup, ...] = ()


class OrphanedClaimsRepository(Protocol):
    def orphaned_claims(self) -> list[tuple[Any, ...]]:
        """(claim_id, assertion_text, state, authority, recorded_at,
        source_paths) for current subject-less claims, evidence paths capped."""

    def related_entities(self) -> list[tuple[Any, ...]]:
        """(claim_id, entity_id, entity_name, entity_kind) for co-mention
        links on the orphaned claims."""

    def entity_names(self) -> list[tuple[Any, ...]]:
        """(entity_id, canonical_name, entity_kind) — the name-match pool."""

    def entity_aliases(self) -> list[tuple[Any, ...]]:
        """(alias, entity_id, entity_name, entity_kind) — the alias pool."""

    def document_paths(self) -> list[tuple[Any, ...]]:
        """(document_id, normalized_path) for all current source documents."""


_GENERIC_FILENAME_TOKENS = {"the", "of", "and", "for", "history", "myth", "lore", "legend"}


def _document_owner_map(
    name_rows: list[tuple[Any, ...]], documents: list[tuple[Any, ...]]
) -> dict[str, tuple[UUID, str]]:
    """Every current document → the entity it represents, document-first.

    An exact stem/name match wins (lore/goodmans-city.md → Goodman's City,
    lore/the-raven-king.md → Raven King, timeline.md → the Timeline entity
    once TKT-0042 mints it); otherwise distinctive stem tokens ⊆ the
    entity's name tokens, longer names outranking shorter (more specific).
    A stem that IS another entity's normalized name never borrows.
    """
    entities = [(row[0], str(row[1]), _normalize_name(str(row[1]))) for row in name_rows]
    by_normalized = {normalized: (entity_id, name) for entity_id, name, normalized in entities}
    resolved: dict[str, tuple[UUID, str]] = {}
    for row in documents:
        path = str(row[1])
        stem = path.lower().rsplit("/", 1)[-1].removesuffix(".md").replace("'", "")
        stem_name = stem.replace("-", " ").replace("_", " ")
        exact = by_normalized.get(stem_name)
        if exact is not None:
            resolved[path] = exact
            continue
        import re as _re

        tokens = [
            token
            for token in _re.split(r"[^a-z0-9]+", stem)
            if len(token) > 2 and token not in _GENERIC_FILENAME_TOKENS
        ]
        if not tokens:
            continue
        best: tuple[int, UUID, str] | None = None
        for entity_id, name, normalized in entities:
            if stem_name in by_normalized and stem_name != normalized:
                continue  # the stem is another entity's exact name
            name_tokens = set(normalized.split(" "))
            if all(token in name_tokens for token in tokens):
                candidate = (len(name_tokens), entity_id, name)
                if best is None or candidate[0] > best[0]:
                    best = candidate
        if best is not None:
            resolved[path] = (best[1], best[2])
    return resolved


_ENCOUNTER_NAME_STOP = {"the", "of", "and", "for"}


def _encounter_group_name(stem: str, parent: str | None) -> str:
    """A per-document encounter name (2026-10-02 ruling: ONE ENCOUNTER PER
    DOCUMENT — a multi-doc directory like Ishirala/ is a GROUP of encounters,
    one per floor). Nested docs carry their parent for context; digits split
    from words ("floor2" -> "Floor 2")."""

    def titled(raw: str) -> list[str]:
        words: list[str] = []
        for token in raw.replace("_", "-").split("-"):
            if not token:
                continue
            head = "".join(ch for ch in token if not ch.isdigit())
            tail = "".join(ch for ch in token if ch.isdigit())
            if head:
                words.append(head if not head.islower() else head.capitalize())
            if tail:
                words.append(tail)
        return words

    stem_words = titled(stem)
    # Nested docs usually repeat their parent in the stem ("ishirala-perch");
    # only prefix the parent when the stem doesn't already carry it
    # ("Return-to-the-Monastery/overview" needs it; "ishirala-floor2" doesn't).
    if parent and not stem.replace("_", "-").replace("/", "-").lower().startswith(
        parent.replace("_", "-").replace("/", "-").lower()
    ):
        stem_words = titled(parent) + stem_words
    parts = stem_words
    parts = [part for index, part in enumerate(parts)
             if len(part) > 2 or part.isdigit() or index > 0]
    return " ".join(parts) or "Encounter"


def _encounter_groups(
    claims: list[OrphanedClaim], name_rows: list[tuple[Any, ...]]
) -> tuple[EncounterGroup, ...]:
    """One encounter per DOCUMENT (the 2026-10-02 ruling): every encounter
    document is its own encounter — "Ishirala Floor 2", "Ishirala Perch" —
    named with its parent directory for context when nested."""
    taken = {_normalize_name(str(row[1])) for row in name_rows}
    grouped: dict[str, dict[str, list | set]] = {}
    for claim in claims:
        if claim.document_owner_id is not None or not claim.source_paths:
            continue
        path = claim.source_paths[0]
        if not path.startswith("encounters/"):
            continue
        rest = path[len("encounters/"):]
        parts = rest.split("/")
        stem = parts[-1].removesuffix(".md")
        parent = "/".join(parts[:-1]) if len(parts) > 1 else None
        if not stem:
            continue
        entry = grouped.setdefault(f"{parent or ''}/{stem}", {"claims": [], "paths": set()})
        entry["claims"].append(claim.claim_id)
        entry["paths"].add(path)
    return tuple(
        EncounterGroup(
            name=name,
            claim_ids=tuple(entry["claims"]),  # type: ignore[arg-type]
            document_paths=tuple(sorted(entry["paths"])),  # type: ignore[arg-type]
            name_available=_normalize_name(name) not in taken,
        )
        for key, entry in sorted(grouped.items(), key=lambda item: -len(item[1]["claims"]))  # type: ignore[index]
        for name in (_encounter_group_name(key.rsplit("/", 1)[-1], key.split("/")[0] if "/" in key else None),)
    )


class OrphanedClaimsService:
    def __init__(self, repository: OrphanedClaimsRepository) -> None:
        self._repository = repository

    def gather(self) -> OrphanedClaimsResult:
        # The document-attachment map (the 2026-09-30 default disposition):
        # evidence path → the entity that document represents, resolved
        # DOCUMENT-FIRST (a record's lore doc must attach even when a
        # locations/ sheet outscores it as the entity's "best" page —
        # lore/goodmans-city.md belongs to Goodman's City alongside its
        # locations/ page). Sessions never match — session notes are not
        # entity documents.
        name_rows = self._repository.entity_names()
        documents = self._repository.document_paths()
        document_owner = _document_owner_map(name_rows, documents)
        related: dict[UUID, list[OrphanOwnerSuggestion]] = {}
        for claim_id, entity_id, name, kind in self._repository.related_entities():
            related.setdefault(claim_id, []).append(
                OrphanOwnerSuggestion(
                    entity_id=entity_id,
                    entity_name=str(name),
                    entity_kind=str(kind),
                    basis="co-mention",
                )
            )
        name_pool = self._repository.entity_names()
        alias_pool = self._repository.entity_aliases()
        claims: list[OrphanedClaim] = []
        with_suggestions = 0
        for row in self._repository.orphaned_claims():
            claim_id = row[0]
            assertion = str(row[1])
            suggestions = self._suggestions(
                claim_id, assertion, related.get(claim_id, []), name_pool, alias_pool
            )
            if suggestions:
                with_suggestions += 1
            paths = tuple(str(p) for p in (row[5] or [])[:_MAX_SOURCE_PATHS])
            attached = document_owner.get(paths[0]) if paths else None
            claims.append(
                OrphanedClaim(
                    claim_id=claim_id,
                    assertion_text=assertion,
                    state=str(row[2]),
                    authority=str(row[3]),
                    recorded_at=str(row[4]) if row[4] is not None else None,
                    source_paths=paths,
                    document_owner_id=attached[0] if attached else None,
                    document_owner_name=attached[1] if attached else None,
                    suggestions=suggestions,
                )
            )
        # Most actionable first (a claim with a suggested owner is one click
        # from the Lore bridge / direct assign when those actions land), then
        # by assertion text for a stable scan order.
        claims.sort(
            key=lambda c: (c.document_owner_id is None and not c.suggestions, c.assertion_text.casefold())
        )
        return OrphanedClaimsResult(
            total_claims=len(claims),
            claims_with_suggestions=with_suggestions,
            claims=tuple(claims),
            encounter_groups=_encounter_groups(claims, name_rows),
        )

    def _suggestions(
        self,
        claim_id: UUID,
        assertion: str,
        co_mentions: list[OrphanOwnerSuggestion],
        name_pool: list[tuple[Any, ...]],
        alias_pool: list[tuple[Any, ...]],
    ) -> tuple[OrphanOwnerSuggestion, ...]:
        seen: set[UUID] = set()
        ranked: list[OrphanOwnerSuggestion] = []
        # Co-mentions first: the link is provenance-recorded evidence, not
        # just string matching. Longest name wins ties (more specific).
        for suggestion in sorted(
            co_mentions, key=lambda s: -len(s.entity_name)
        ):
            if suggestion.entity_id not in seen:
                seen.add(suggestion.entity_id)
                ranked.append(suggestion)
        if len(ranked) >= _MAX_SUGGESTIONS:
            return tuple(ranked[:_MAX_SUGGESTIONS])
        # Name-in-text matches fill the remaining slots (the shared matcher).
        for match in suggest_owner_matches(
            assertion, name_pool, alias_pool,
            limit=_MAX_SUGGESTIONS - len(ranked), exclude=seen,
        ):
            ranked.append(
                OrphanOwnerSuggestion(
                    entity_id=match.entity_id,
                    entity_name=match.entity_name,
                    entity_kind=match.entity_kind,
                    basis="name in text",
                )
            )
        return tuple(ranked)
