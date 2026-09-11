"""PostgreSQL repository for candidate extraction enrichment (TKT-0035)."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.candidate_extraction import (
    ExtractedCandidateDimension,
)
from dm_assistant_core.domain.extraction import (
    DocumentContext,
    ExtractionAttemptFailure,
    ExtractionAuthority,
    SegmentCoverage,
    SourceSegment,
    SubjectResolution,
)
from dm_assistant_core.domain.models import ClaimState, Visibility
from dm_assistant_core.importer.models import CandidateAuthority


class PostgresCandidateExtractionRepository:
    """Read candidate assertion text and persist extracted dimensions."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def load_candidate_context(
        self, candidate_id: UUID
    ) -> tuple[str, DocumentContext | None] | None:
        with self._database.connection() as connection:
            row = connection.execute(
                """
                SELECT ic.assertion_text,
                       coalesce(sdp.normalized_path, sd.original_path),
                       sr.frontmatter_json,
                       sr.raw_content,
                       ic.state,
                       ic.authority,
                       ic.visibility
                FROM import_candidates ic
                JOIN source_documents sd ON sd.id = ic.source_document_id
                LEFT JOIN source_document_paths sdp
                    ON sdp.source_document_id = sd.id AND sdp.is_current
                LEFT JOIN LATERAL (
                    SELECT sr2.frontmatter_json, sr2.raw_content
                    FROM source_revisions sr2
                    WHERE sr2.source_document_id = sd.id
                    ORDER BY sr2.captured_at DESC, sr2.id DESC
                    LIMIT 1
                ) sr ON true
                WHERE ic.id = %s
                """,
                (candidate_id,),
            ).fetchone()
        if row is None:
            return None
        assertion_text = str(row[0])
        source_path = str(row[1]) if row[1] else "unknown"
        frontmatter = dict(row[2]) if row[2] else {}
        heading = _extract_heading(bytes(row[3])) if row[3] else None
        record_type = _record_type(source_path)
        context = DocumentContext(
            source_path=source_path,
            heading=heading,
            frontmatter=frontmatter,
            focal_subject=heading if record_type in {"pc", "npc", "location"} else None,
            record_type=record_type,
            candidate_state=ClaimState(str(row[4])),
            candidate_authority=ExtractionAuthority(str(row[5])),
            candidate_visibility=Visibility(str(row[6])),
        )
        return (assertion_text, context)

    def replace_extractions(
        self,
        candidate_id: UUID,
        extractions: tuple[ExtractedCandidateDimension, ...],
        extractor_version: str,
        segments: tuple[SourceSegment, ...],
        coverage: tuple[SegmentCoverage, ...],
        model_profile_key: str | None = None,
        model_slug: str | None = None,
        prompt_version: str | None = None,
    ) -> tuple[ExtractedCandidateDimension, ...]:
        with self._database.connection() as connection:
            run_id = uuid4()
            connection.execute(
                """
                INSERT INTO candidate_extraction_runs (
                    id, candidate_id, extractor_version, segments_json, coverage_json,
                    model_profile_key, model_slug, prompt_version, created_at
                ) VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, now())
                """,
                (
                    run_id,
                    candidate_id,
                    extractor_version,
                    json.dumps([item.model_dump(mode="json") for item in segments]),
                    json.dumps([item.model_dump(mode="json") for item in coverage]),
                    model_profile_key,
                    model_slug,
                    prompt_version,
                ),
            )
            for dim in extractions:
                connection.execute(
                    """
                    INSERT INTO candidate_extractions (
                        id, candidate_id, extraction_run_id, subject, predicate, object_entity,
                        assertion_text, supporting_excerpt, state, authority, visibility,
                        confidence, extractor_version, created_at, source_segment_ids,
                        subject_resolution
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        dim.extraction_id,
                        candidate_id,
                        run_id,
                        dim.subject,
                        dim.predicate,
                        dim.object_entity,
                        dim.assertion_text,
                        dim.supporting_excerpt,
                        dim.state.value,
                        dim.authority.value,
                        dim.visibility.value,
                        str(dim.confidence),
                        dim.extractor_version,
                        dim.created_at,
                        list(dim.source_segment_ids),
                        dim.subject_resolution.value,
                    ),
                )
        return self.load_extractions(candidate_id)

    def record_failure(
        self,
        candidate_id: UUID,
        failures: tuple[ExtractionAttemptFailure, ...],
        extractor_version: str,
        model_profile_key: str | None,
        model_slug: str | None,
        prompt_version: str | None,
    ) -> None:
        failure_group_id = uuid4()
        with self._database.connection() as connection:
            for failure in failures:
                connection.execute(
                    """
                    INSERT INTO candidate_extraction_failures (
                        id, failure_group_id, candidate_id, attempt_number, error,
                        raw_response, extractor_version, model_profile_key, model_slug,
                        prompt_version, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                    """,
                    (
                        uuid4(),
                        failure_group_id,
                        candidate_id,
                        failure.attempt_number,
                        failure.error,
                        failure.raw_response,
                        extractor_version,
                        model_profile_key,
                        model_slug,
                        prompt_version,
                    ),
                )

    def load_extractions(self, candidate_id: UUID) -> tuple[ExtractedCandidateDimension, ...]:
        with self._database.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, candidate_id, subject, predicate, object_entity,
                       assertion_text, supporting_excerpt, state, authority, visibility,
                       confidence, extractor_version, created_at, source_segment_ids,
                       subject_resolution
                 FROM candidate_extractions
                 WHERE extraction_run_id = (
                       SELECT id FROM candidate_extraction_runs
                       WHERE candidate_id = %s
                       ORDER BY created_at DESC, id DESC LIMIT 1
                 )
                 ORDER BY created_at, id
                """,
                (candidate_id,),
            ).fetchall()
        return tuple(_to_dimension(row) for row in rows)


def _to_dimension(row: tuple[Any, ...]) -> ExtractedCandidateDimension:
    return ExtractedCandidateDimension(
        extraction_id=row[0],
        candidate_id=row[1],
        subject=str(row[2]),
        subject_resolution=SubjectResolution(str(row[14])),
        predicate=str(row[3]) if row[3] is not None else None,
        object_entity=str(row[4]) if row[4] is not None else None,
        assertion_text=str(row[5]),
        supporting_excerpt=str(row[6]),
        state=ClaimState(str(row[7])),
        authority=CandidateAuthority(str(row[8])),
        visibility=Visibility(str(row[9])),
        confidence=Decimal(str(row[10])),
        extractor_version=str(row[11]),
        created_at=row[12],
        source_segment_ids=tuple(str(item) for item in row[13]),
    )


def _extract_heading(raw_content: bytes) -> str | None:
    """Extract the first Markdown H1 heading from raw source content."""
    import re

    try:
        text = raw_content.decode("utf-8", errors="replace")
    except Exception:
        return None
    match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def _record_type(source_path: str) -> str | None:
    top_level = source_path.replace("\\", "/").split("/", 1)[0].lower()
    return {"pcs": "pc", "npcs": "npc", "locations": "location"}.get(top_level)
