"""Standing entity/document link audit (TKT-0110).

Read-only traversal that surfaces wrong-page borrows, ambiguous matches, and
zero-affinity identities across all entities with claim-evidenced sources.
Findings are computed live — never stored as truth; every fix stays an
explicit DM decision or a matcher rule change with tests.
"""

from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# Generic words a lore writeup may append to the entity's name; a filename
# using anything beyond the entity's own distinctive tokens is a foreign
# subject (mirrors the UI matcher's rule).
_FILENAME_GENERIC = {"the", "of", "and", "for", "history", "myth", "lore", "legend"}


class LinkFinding(BaseModel):
    model_config = ConfigDict(frozen=True)
    kind: str  # wrong_page_borrow | ambiguous_match | zero_affinity | orphan_page
    entity_id: UUID | None
    entity_name: str
    entity_kind: str
    document_id: UUID | None
    document_path: str | None
    detail: str


class LinkAuditResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    audited_at: datetime
    findings: tuple[LinkFinding, ...]


class LinkAuditRepository(Protocol):
    def entities_with_sources(self) -> list[tuple[UUID, str, str, list[tuple[UUID, str]]]]:
        """(entity_id, canonical_name, entity_kind, [(document_id, path)]) for
        every identity with at least one claim-evidenced source."""

    def all_entity_names(self) -> list[str]:
        """All canonical names, for the foreign-token check."""


def _stem_tokens(path: str) -> set[str]:
    stem = path.rsplit("/", 1)[-1].removesuffix(".md").replace("-", " ").replace("'", "").replace("’", "")
    return {t for t in stem.lower().split() if len(t) > 2 and t not in _FILENAME_GENERIC}


def _name_tokens(name: str) -> set[str]:
    cleaned = name.replace("'", "").replace("’", "").lower()
    return {t for t in cleaned.split() if len(t) > 2 and t not in {"the", "of", "and", "for"}}


class LinkAuditService:
    def __init__(self, repository: LinkAuditRepository) -> None:
        self._repository = repository

    def audit(self) -> LinkAuditResult:
        entities = self._repository.entities_with_sources()
        # Build a word-to-entity-names index so a foreign filename token can
        # be attributed to the entity whose name contains it.
        word_index: dict[str, list[str]] = {}
        for full_name in self._repository.all_entity_names():
            for token in _name_tokens(full_name):
                word_index.setdefault(token, []).append(full_name)
        findings: list[LinkFinding] = []

        for entity_id, name, kind, sources in entities:
            name_tokens = _name_tokens(name)
            if not name_tokens:
                continue
            exact_matches = []
            for doc_id, path in sources:
                stem = _stem_tokens(path)
                if not stem:
                    continue
                if stem == name_tokens:
                    exact_matches.append((doc_id, path))
                elif not stem.issubset(name_tokens):
                    foreign = stem - name_tokens
                    foreign_named = sorted({
                        owner
                        for token in foreign
                        for owner in word_index.get(token, [])
                        if owner.lower() != name.lower()
                    })
                    if foreign_named:
                        findings.append(LinkFinding(
                            kind="wrong_page_borrow",
                            entity_id=entity_id, entity_name=name, entity_kind=kind,
                            document_id=doc_id, document_path=path,
                            detail=(f"'{path}' carries tokens belonging to other entities: "
                                    + ", ".join(foreign_named)
                                    + " — this document may be another subject's page borrowed as evidence"),
                        ))
            if not exact_matches and len(sources) > 3:
                # No source's filename names this entity, but it has many
                # claim-evidenced sources — a possible zero-affinity identity
                # whose claims all live in other subjects' files.
                findings.append(LinkFinding(
                    kind="zero_affinity",
                    entity_id=entity_id, entity_name=name, entity_kind=kind,
                    document_id=None, document_path=None,
                    detail=(f"{len(sources)} claim-evidenced sources, none of which "
                            f"is this entity's page (no filename matches '{name}') "
                            "— the identity may have no file of its own"),
                ))

        return LinkAuditResult(
            audited_at=datetime.now(UTC),
            findings=tuple(findings),
        )
