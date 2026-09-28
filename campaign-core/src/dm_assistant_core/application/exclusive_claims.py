"""Step 1 of the Migration→Seeded campaign (TKT-0140, Sean's ruling
2026-09-22): for every unqualified entity, the claims evidenced ONLY on the
document that represents it — the migration's provenance-first output whose
ownership was never assigned — ready for one Assign Ownership action.
"""

from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExclusiveClaim(BaseModel):
    model_config = ConfigDict(frozen=True)

    claim_id: UUID
    assertion_text: str
    state: str
    owner_entity_id: UUID | None = None
    owner_name: str | None = None


class EntityDocumentClaims(BaseModel):
    model_config = ConfigDict(frozen=True)

    entity_id: UUID
    canonical_name: str
    entity_kind: str
    document_id: UUID | None = None
    document_path: str | None = None
    claims: tuple[ExclusiveClaim, ...] = ()


class ExclusiveClaimsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    entities_with_exclusive_claims: int
    total_claims: int
    groups: tuple[EntityDocumentClaims, ...] = ()


# Generic words a lore writeup may append to the entity's name — mirrors the
# client matcher's rule.
_FILENAME_GENERIC = {"the", "of", "and", "for", "history", "myth", "lore", "legend"}
_PREFERRED_ROOTS = {"pc": "pcs/", "npc": "npcs/", "location": "locations/"}


def _normalize_name(name: str) -> str:
    lowered = name.lower().replace("'", "").replace("’", "")
    return " ".join(part for part in __import__("re").split(r"[^a-z0-9]+", lowered) if part)


class ExclusiveClaimsRepository(Protocol):
    def unqualified_entities(self) -> list[tuple[Any, ...]]:
        """(entity_id, canonical_name, entity_kind) for Q1-failing entities."""

    def document_paths(self) -> list[tuple[Any, ...]]:
        """(document_id, normalized_path) for all current source documents."""

    def entity_names(self) -> list[tuple[Any, ...]]:
        """(id, canonical_name) for the foreign-name exclusion."""

    def claims_exclusive_to(self, document_id: UUID) -> list[tuple[Any, ...]]:
        """(claim_id, assertion_text, state, subject_entity_id, owner_name)
        for current claims evidenced ONLY on this document."""


class ExclusiveClaimsService:
    def __init__(self, repository: ExclusiveClaimsRepository) -> None:
        self._repository = repository

    def gather(self) -> ExclusiveClaimsResult:
        unqualified = self._repository.unqualified_entities()
        documents = self._repository.document_paths()
        names = {
            _normalize_name(str(row[1])): row[0]
            for row in self._repository.entity_names()
        }
        groups: list[EntityDocumentClaims] = []
        total = 0
        for entity_id, canonical_name, kind in unqualified:
            document = self._match_document(
                str(canonical_name), str(kind), documents, names
            )
            claims: tuple[ExclusiveClaim, ...] = ()
            if document is not None:
                claims = tuple(
                    ExclusiveClaim(
                        claim_id=row[0],
                        assertion_text=str(row[1]),
                        state=str(row[2]),
                        owner_entity_id=row[3],
                        owner_name=str(row[4]) if row[4] is not None else None,
                    )
                    for row in self._repository.claims_exclusive_to(document[0])
                )
            if document is not None and claims:
                total += len(claims)
                groups.append(
                    EntityDocumentClaims(
                        entity_id=entity_id,
                        canonical_name=str(canonical_name),
                        entity_kind=str(kind),
                        document_id=document[0],
                        document_path=document[1],
                        claims=claims,
                    )
                )
        return ExclusiveClaimsResult(
            entities_with_exclusive_claims=len(groups),
            total_claims=total,
            groups=tuple(groups),
        )

    def _match_document(
        self,
        canonical_name: str,
        kind: str,
        documents: list[tuple[Any, ...]],
        names: dict[str, UUID],
    ) -> tuple[Any, ...] | None:
        """The client page matcher's essential rules, server-side: the
        authored entities/{slug} page wins; an exact filename match next;
        otherwise a filename using nothing beyond the entity's distinctive
        name tokens (never another entity's exact name)."""
        import re

        normalized = _normalize_name(canonical_name)
        slug = re.sub(r"[^a-z0-9]+", "-", canonical_name.lower()).strip("-")
        name_tokens = {
            token
            for token in normalized.split(" ")
            if len(token) > 2 and token not in {"the", "of", "and", "for"}
        }
        preferred_root = _PREFERRED_ROOTS.get(kind)
        other_names = {n for n in names if n != normalized}

        def stem(path: str) -> str:
            return path.lower().rsplit("/", 1)[-1].removesuffix(".md").replace("'", "")

        def stem_tokens(path: str) -> list[str]:
            return [
                token
                for token in re.split(r"[^a-z0-9]+", stem(path))
                if len(token) > 2 and token not in _FILENAME_GENERIC
            ]

        def score(path: str, base: int) -> tuple[int, int]:
            rooted = (
                2
                if path.lower().startswith("entities/")
                else 1
                if preferred_root and path.lower().startswith(preferred_root)
                else 0
            )
            return base * 10 + rooted, len(stem_tokens(path))

        exact = [d for d in documents if stem(str(d[1])).replace("-", " ") == normalized]
        pool = exact or [
            d
            for d in documents
            if stem(str(d[1])).replace("-", " ") not in other_names
            and (tokens := stem_tokens(str(d[1])))
            and all(token in name_tokens for token in tokens)
        ]
        if not pool:
            return None
        return sorted(
            pool,
            key=lambda d: (score(str(d[1]), 1), str(d[1])),
            reverse=True,
        )[0]
