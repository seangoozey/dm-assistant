"""Standing unpromoted-material audit — the Promotion Pipeline repair lane
(ADR-0018 pt 6, TKT-0136).

In-app writing leaves material short of canon: entities with an authored page
but no claims (pre-pipeline descriptions), direct captures with statements
still pending review, brainstorm sessions with unpromoted thoughts. Findings
are computed live and re-runnable — a standing review, never a backfill.
Every fix routes through the surface's reviewed door; correcting already-
promoted claims flows through the existing receipted supersession lanes.
"""

from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UnpromotedFinding(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: str  # empty_shell | pending_capture | unpromoted_thoughts
    entity_id: UUID | None = None
    entity_name: str
    entity_kind: str | None = None
    document_id: UUID | None = None
    document_path: str | None = None
    session_id: UUID | None = None
    count: int = 0
    detail: str


class UnpromotedAuditResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    audited_at: datetime
    findings: tuple[UnpromotedFinding, ...]


class UnpromotedAuditRepository(Protocol):
    def empty_shells(self) -> list[tuple[Any, ...]]:
        """(entity_id, canonical_name, entity_kind, page_document_id) for
        entities with an authored description page and zero current claims."""

    def pending_captures(self) -> list[tuple[Any, ...]]:
        """(document_id, path, kind, pending_count) for direct-input documents
        with statements still awaiting review."""

    def unpromoted_thoughts(self) -> list[tuple[Any, ...]]:
        """(session_id, title, pending_count) for brainstorm sessions whose
        thought candidates were never promoted."""


class UnpromotedAuditService:
    def __init__(self, repository: UnpromotedAuditRepository) -> None:
        self._repository = repository

    def audit(self) -> UnpromotedAuditResult:
        findings: list[UnpromotedFinding] = []
        for entity_id, name, kind, page_document_id in self._repository.empty_shells():
            findings.append(
                UnpromotedFinding(
                    kind="empty_shell",
                    entity_id=entity_id,
                    entity_name=str(name),
                    entity_kind=str(kind),
                    document_id=page_document_id,
                    detail=(
                        "has an authored page but no claims — its statements "
                        "were never promoted (revise the description through "
                        "promotion review)"
                    ),
                )
            )
        for document_id, path, kind, pending in self._repository.pending_captures():
            findings.append(
                UnpromotedFinding(
                    kind="pending_capture",
                    document_id=document_id,
                    document_path=str(path),
                    entity_name=str(path),
                    entity_kind=str(kind) if kind else None,
                    count=int(pending),
                    detail=(
                        f"{int(pending)} captured statement{'s' if int(pending) != 1 else ''} "
                        "still awaiting review"
                    ),
                )
            )
        for session_id, title, pending in self._repository.unpromoted_thoughts():
            findings.append(
                UnpromotedFinding(
                    kind="unpromoted_thoughts",
                    session_id=session_id,
                    entity_name=str(title),
                    count=int(pending),
                    detail=(
                        f"{int(pending)} thought{'s' if int(pending) != 1 else ''} "
                        "never promoted — reopen the brainstorm"
                    ),
                )
            )
        return UnpromotedAuditResult(
            audited_at=datetime.now(UTC), findings=tuple(findings)
        )
