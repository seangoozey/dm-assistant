"""Direct human input captured as immutable evidence before canonical review."""

import re
from datetime import UTC, date, datetime
from hashlib import sha256
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from dm_assistant_core.application.imports import MarkdownImportService
from dm_assistant_core.domain import ClaimState, Visibility
from dm_assistant_core.domain.chronology import CampaignDate
from dm_assistant_core.importer import (
    CandidateAuthority,
    ImportCandidate,
    ImportClassification,
    ImportOutcome,
    MarkdownScanBatch,
    ScannedSource,
)


class DirectInputMention(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    entity_id: UUID
    display_name: str = Field(min_length=1)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)


class SessionNoteCaptureCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    session_date: date
    in_game_date: CampaignDate
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    visibility: Visibility = Visibility.DM_ONLY
    mentions: tuple[DirectInputMention, ...] = ()
    capture_id: UUID | None = None
    idempotency_key: str = Field(min_length=1)


class SessionNoteCaptureReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    capture_id: UUID
    source_document_id: UUID
    source_revision_id: UUID
    candidate_id: UUID
    candidate_ids: tuple[UUID, ...]
    idempotent_replay: bool


class CampaignClockRepository(Protocol):
    def get_current(self) -> CampaignDate | None: ...
    def set_current(self, value: CampaignDate) -> None: ...


class SessionNoteCaptureService:
    def __init__(self, imports: MarkdownImportService, clock: CampaignClockRepository) -> None:
        self._imports = imports
        self._clock = clock

    def current_date(self) -> CampaignDate | None:
        return self._clock.get_current()

    def capture(self, command: SessionNoteCaptureCommand) -> SessionNoteCaptureReceipt:
        if not command.in_game_date.is_complete():
            raise ValueError("session notes require a complete in-game date")
        now = datetime.now(UTC)
        capture_id = command.capture_id or uuid4()
        title = command.title.strip()
        content = command.text.encode("utf-8")
        mention_payload = []
        for mention in command.mentions:
            token = command.text[mention.start_offset : mention.end_offset]
            if token != f"@{mention.display_name}":
                raise ValueError(f"mention offsets do not match @{mention.display_name}")
            mention_payload.append(mention.model_dump(mode="json"))
        slug = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-") or "session"
        path = f"sessions/notes/{command.session_date.isoformat()}-{slug}-{str(capture_id)[:8]}"
        candidates = []
        statement_number = 0
        for line_match in re.finditer(r"(?m)^[^\r\n]*\S[^\r\n]*", command.text):
            for match in re.finditer(r".+?(?:[.!?]+(?=\s|$)|$)", line_match.group()):
                raw = match.group()
                if not raw.strip():
                    continue
                left_trim = len(raw) - len(raw.lstrip())
                right_trim = len(raw.rstrip())
                start = line_match.start() + match.start() + left_trim
                end = line_match.start() + match.start() + right_trim
                statement_number += 1
                assertion = re.sub(r"@(?=[A-Za-z0-9])", "", command.text[start:end])
                fingerprint = sha256(
                    f"direct-input/session-note-v3\x00{start}\x00{end}\x00{assertion}".encode()
                ).hexdigest()
                candidates.append(
                    ImportCandidate(
                        fingerprint=fingerprint,
                        section=f"Session Notes / Statement {statement_number}",
                        assertion_text=assertion,
                        state=ClaimState.OBSERVED,
                        authority=CandidateAuthority.REAL_PLAY,
                        visibility=command.visibility,
                        start_offset=start,
                        end_offset=end,
                        extractor_version="direct-input/session-note-v3",
                    )
                )
        if not candidates:
            raise ValueError("session notes require at least one non-empty line")
        source = ScannedSource(
            path=path,
            content_hash=sha256(content).hexdigest(),
            content=content,
            filesystem_modified_at=now,
            external_id=str(capture_id),
            canonical_name=title,
            frontmatter={
                "type": "session_note",
                "name": title,
                "session_date": command.session_date.isoformat(),
                "in_game_date": command.in_game_date.model_dump(mode="json"),
                "capture_mode": "direct_input",
                "mentions": mention_payload,
            },
            classification=ImportClassification.REAL_PLAY_EVIDENCE,
            proposed_outcome=ImportOutcome.NEW,
            candidates=tuple(candidates),
            entity_candidates=0,
            warnings=(),
        )
        receipt = self._imports.ingest(
            MarkdownScanBatch(
                root_identifier=f"direct-input:session-note:{capture_id}",
                snapshot_at=now,
                importer_version="direct-input/session-note-v3",
                parser_version="direct-input/session-note-v2",
                path_policy_version="direct-input/session-note-v2",
                idempotency_key=command.idempotency_key,
                excluded_paths_encountered=(),
                files=(source,),
            )
        )
        outcome = receipt.observation.files[0]
        if (
            not outcome.source_document_id
            or not outcome.source_revision_id
            or not outcome.candidate_ids
        ):
            raise RuntimeError("session-note capture did not produce reviewable evidence")
        self._clock.set_current(command.in_game_date)
        return SessionNoteCaptureReceipt(
            capture_id=capture_id,
            source_document_id=outcome.source_document_id,
            source_revision_id=outcome.source_revision_id,
            candidate_id=outcome.candidate_ids[0],
            candidate_ids=outcome.candidate_ids,
            idempotent_replay=receipt.idempotent_replay,
        )
