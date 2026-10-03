"""Deterministic owner suggestions for statement/claim text (TKT-0148).

The same matching the orphaned-claims review uses (TKT-0138), extracted as
the shared module: canonical names and aliases matched word-boundary,
apostrophe-tolerant, longest-name-first (more specific wins), capped. Never
authoritative — a suggestion is a preselection the DM confirms, changes, or
overrides with the explicit no-owner choice (ADR-0021: sessions and
brainstorms assign ownership at commit; nothing enters canon ownerless by
omission).
"""

import re
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_LIMIT = 3


class OwnerSuggestion(BaseModel):
    model_config = ConfigDict(frozen=True)

    entity_id: UUID
    entity_name: str
    entity_kind: str
    basis: str = "name in text"


class OwnerSuggestionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    suggestions: tuple[OwnerSuggestion, ...]


class OwnerSuggestionRepository(Protocol):
    def entity_names(self) -> list[tuple[Any, ...]]:
        """(entity_id, canonical_name, entity_kind)"""

    def entity_aliases(self) -> list[tuple[Any, ...]]:
        """(alias, entity_id, canonical_name, entity_kind)"""


def name_pattern(name: str) -> re.Pattern[str] | None:
    """Word-boundary pattern for a name, apostrophe-tolerant (Ishi'ra'la)."""
    cleaned = name.strip()
    if len(cleaned) < 3:
        return None
    escaped = re.escape(cleaned).replace(r"\ ", r"[\s\-]+")
    return re.compile(rf"(?<![\w']){escaped}(?![\w'])", re.IGNORECASE)


def suggest_owner_matches(
    text: str,
    name_pool: list[tuple[Any, ...]],
    alias_pool: list[tuple[Any, ...]],
    limit: int = DEFAULT_LIMIT,
    exclude: set[UUID] | None = None,
) -> list[OwnerSuggestion]:
    """Rank entities whose name/alias appears in ``text``, longest first."""
    candidates: list[tuple[int, str, UUID, str, str]] = []
    seen: set[UUID] = set(exclude or ())
    for entry in (
        [(str(row[1]), row[0], str(row[2])) for row in name_pool]
        + [(str(row[0]), row[1], str(row[3])) for row in alias_pool]
    ):
        name, entity_id, kind = entry
        pattern = name_pattern(name)
        if pattern is None or entity_id in seen:
            continue
        if pattern.search(text):
            display = next(
                (str(row[1]) for row in name_pool if row[0] == entity_id), name
            )
            candidates.append((len(name), display, entity_id, kind, name))
    candidates.sort(key=lambda c: (-c[0], c[1].casefold()))
    suggestions: list[OwnerSuggestion] = []
    for _length, display, entity_id, kind, _matched in candidates:
        if len(suggestions) >= limit:
            break
        seen.add(entity_id)
        suggestions.append(
            OwnerSuggestion(entity_id=entity_id, entity_name=display, entity_kind=kind)
        )
    return suggestions


class OwnerSuggestionService:
    def __init__(self, repository: OwnerSuggestionRepository) -> None:
        self._repository = repository

    def suggest(self, text: str, limit: int = Field(default=DEFAULT_LIMIT)) -> OwnerSuggestionResult:
        return OwnerSuggestionResult(
            text=text,
            suggestions=tuple(
                suggest_owner_matches(
                    text, self._repository.entity_names(), self._repository.entity_aliases(), limit
                )
            ),
        )
