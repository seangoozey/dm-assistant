"""PostgreSQL read adapter for import receipts, candidates, and reviews."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.import_reviews import (
    CandidateEvidence,
    CandidateExtractionReview,
    CandidateExtractionSegmentReview,
    CandidateListQuery,
    ClaimProjection,
    DispositionSourceReviewCommand,
    ImportCandidatePage,
    ImportCandidateReview,
    ImportReviewItem,
    ImportReviewItemPage,
    ImportRunDetail,
    ImportRunListQuery,
    ImportRunPage,
    ImportRunSummary,
    ReviewItemListQuery,
    SourceDocumentClaim,
    SourceDocumentClaimHistory,
    SourceDocumentContent,
    SourceDocumentListQuery,
    SourceDocumentPage,
    SourceDocumentSummary,
    SourceReviewDispositionError,
    SourceReviewDispositionResult,
)
from dm_assistant_core.domain import ClaimState, RequesterRole, RequesterVisibility, Visibility
from dm_assistant_core.domain.extraction import SubjectResolution
from dm_assistant_core.importer import CandidateAuthority, ImportClassification, ImportReceipt


class PostgresImportReviewRepository:
    """Read imported evidence without changing review or canonical state."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def list_runs(self, query: ImportRunListQuery) -> ImportRunPage:
        where, parameters = _run_filters(query)
        with self._database.connection() as connection:
            total_row = connection.execute(
                f"SELECT count(*) FROM import_runs ir {where}", parameters
            ).fetchone()
            rows = connection.execute(
                "SELECT ir.status, ir.receipt_json FROM import_runs ir "
                f"{where} ORDER BY ir.started_at DESC, ir.id DESC LIMIT %s OFFSET %s",
                (*parameters, query.limit, query.offset),
            ).fetchall()
        assert total_row is not None
        items = tuple(
            _run_summary(str(row[0]), ImportReceipt.model_validate(row[1])) for row in rows
        )
        return ImportRunPage(
            items=items, total=int(total_row[0]), limit=query.limit, offset=query.offset
        )

    def get_run(self, run_id: UUID) -> ImportRunDetail | None:
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT status, receipt_json FROM import_runs WHERE id = %s", (run_id,)
            ).fetchone()
        if row is None:
            return None
        receipt = ImportReceipt.model_validate(row[1])
        return ImportRunDetail(summary=_run_summary(str(row[0]), receipt), receipt=receipt)

    def disposition_source_review(
        self, command: DispositionSourceReviewCommand
    ) -> SourceReviewDispositionResult:
        disposition_id = uuid4()
        created_at = datetime.now(UTC)
        with self._database.connection() as connection:
            review = connection.execute(
                "SELECT status FROM review_items WHERE id = %s FOR UPDATE", (command.review_id,)
            ).fetchone()
            if review is None:
                raise SourceReviewDispositionError("source review not found")
            if str(review[0]) == "resolved":
                existing = connection.execute(
                    "SELECT id, decision, reason, created_at "
                    "FROM source_review_dispositions WHERE review_id = %s",
                    (command.review_id,),
                ).fetchone()
                if existing is None:
                    raise SourceReviewDispositionError("source review is already resolved")
                return SourceReviewDispositionResult(
                    disposition_id=existing[0],
                    review_id=command.review_id,
                    decision=str(existing[1]),
                    reason=str(existing[2]),
                    created_at=existing[3],
                )
            if str(review[0]) != "open":
                raise SourceReviewDispositionError(
                    f"source review status {review[0]} cannot be resolved"
                )
            connection.execute(
                "INSERT INTO source_review_dispositions"
                "(id, review_id, decision, reason, created_at) VALUES (%s,%s,%s,%s,%s)",
                (disposition_id, command.review_id, command.decision, command.reason, created_at),
            )
            connection.execute(
                "UPDATE review_items SET status='resolved', updated_at=%s WHERE id=%s",
                (created_at, command.review_id),
            )
        return SourceReviewDispositionResult(
            disposition_id=disposition_id,
            review_id=command.review_id,
            decision=command.decision,
            reason=command.reason,
            created_at=created_at,
        )

    def list_candidates(self, query: CandidateListQuery) -> ImportCandidatePage:
        where, parameters = _candidate_filters(query)
        with self._database.connection() as connection:
            total_row = connection.execute(
                f"SELECT count(*) FROM import_candidates ic {where}", parameters
            ).fetchone()
            id_rows = connection.execute(
                "SELECT ic.id FROM import_candidates ic "
                f"{where} ORDER BY ic.created_at, "
                "COALESCE((SELECT min(ice.start_offset) FROM import_candidate_evidence ice "
                "WHERE ice.candidate_id = ic.id), 0), "
                "ic.id LIMIT %s OFFSET %s",
                (*parameters, query.limit, query.offset),
            ).fetchall()
            items = tuple(
                candidate
                for (candidate_id,) in id_rows
                if (candidate := _load_candidate(connection, candidate_id)) is not None
            )
        assert total_row is not None
        return ImportCandidatePage(
            items=items, total=int(total_row[0]), limit=query.limit, offset=query.offset
        )

    def get_candidate(
        self, candidate_id: UUID, requester: RequesterVisibility
    ) -> ImportCandidateReview | None:
        where, parameters = _candidate_visibility(requester)
        with self._database.connection() as connection:
            row = connection.execute(
                f"SELECT ic.id FROM import_candidates ic WHERE ic.id = %s {where}",
                (candidate_id, *parameters),
            ).fetchone()
            if row is None:
                return None
            return _load_candidate(connection, candidate_id)

    def list_reviews(self, query: ReviewItemListQuery) -> ImportReviewItemPage:
        where, parameters = _review_filters(query)
        source_lateral = _REVIEW_SOURCE_LATERAL
        with self._database.connection() as connection:
            total_row = connection.execute(
                "SELECT count(*) FROM review_items ri " + source_lateral + where,
                parameters,
            ).fetchone()
            rows = connection.execute(
                "SELECT ri.id, ri.kind, ri.status, ri.subject_type, ri.subject_id, "
                "ri.details, ri.opened_by_import_run_id, ri.created_at, ri.updated_at, "
                "coalesce(ri.details->>'path', source.source_path), "
                "coalesce(ri.details->>'classification', source.classification) "
                "FROM review_items ri "
                + source_lateral
                + where
                + " ORDER BY ri.created_at, ri.id LIMIT %s OFFSET %s",
                (*parameters, query.limit, query.offset),
            ).fetchall()
        assert total_row is not None
        items = tuple(
            ImportReviewItem(
                review_id=row[0],
                kind=str(row[1]),
                status=str(row[2]),
                subject_type=str(row[3]),
                subject_id=row[4],
                details=dict(row[5]),
                opened_by_import_run_id=row[6],
                created_at=row[7],
                updated_at=row[8],
                source_path=str(row[9]) if row[9] is not None else None,
                classification=str(row[10]) if row[10] is not None else None,
            )
            for row in rows
        )
        return ImportReviewItemPage(
            items=items, total=int(total_row[0]), limit=query.limit, offset=query.offset
        )

    def list_source_documents(self, query: SourceDocumentListQuery) -> SourceDocumentPage:
        with self._database.connection() as connection:
            total_row = connection.execute(
                "SELECT count(DISTINCT sd.id) "
                "FROM source_documents sd "
                "JOIN source_document_paths sdp ON sdp.source_document_id = sd.id "
                "    AND sdp.is_current AND sdp.connector = sd.connector"
            ).fetchone()
            rows = connection.execute(_SOURCE_DOCUMENTS_SQL).fetchall()
        assert total_row is not None
        items = tuple(_source_document_row(row) for row in rows)
        return SourceDocumentPage(
            items=items,
            total=int(total_row[0]),
            limit=query.limit,
            offset=query.offset,
        )

    def get_source_document_content(self, document_id: UUID) -> SourceDocumentContent | None:
        with self._database.connection() as connection:
            row = connection.execute(_SOURCE_DOCUMENT_CONTENT_SQL, (document_id,)).fetchone()
            claim_rows = connection.execute(
                "SELECT DISTINCT ON (c.id) c.id, c.assertion_text, c.state::text, "
                "c.authority::text, c.visibility, c.is_conditional, cc.trigger_text, "
                "c.recorded_at, CASE "
                "WHEN c.state = 'intended' AND c.authority IN ('real_play', 'dm_correction') "
                "AND NOT c.predicts_subject_action THEN 'player_plan' "
                "WHEN c.authority IN ('real_play', 'dm_correction') THEN 'real_play' "
                "WHEN c.authority = 'npc_intention' THEN 'npc_plan' "
                "WHEN c.authority IN ('brainstorm', 'preparation') THEN 'dm_plan' "
                "WHEN c.state = 'intended' AND c.predicts_subject_action THEN 'player_plan' "
                "ELSE 'lore_fact' END, "
                "substring(convert_from(sr.raw_content, 'UTF8') "
                "from ss.start_offset + 1 for ss.end_offset - ss.start_offset), "
                "c.subject_entity_id, se.canonical_name "
                "FROM claims c "
                "JOIN claim_evidence evidence ON evidence.claim_id = c.id "
                "JOIN source_spans ss ON ss.id = evidence.source_span_id "
                "JOIN source_revisions sr ON sr.id = ss.source_revision_id "
                "LEFT JOIN entities se ON se.id = c.subject_entity_id "
                "LEFT JOIN claim_conditions cc ON cc.claim_id = c.id "
                "WHERE sr.source_document_id = %s "
                "AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs "
                "WHERE cs.superseded_claim_id = c.id) "
                "ORDER BY c.id, ss.start_offset",
                (document_id,),
            ).fetchall()
            history_rows = connection.execute(
                "SELECT DISTINCT ON (c.id) c.id, c.assertion_text, c.state::text, "
                "c.authority::text, c.visibility, c.is_conditional, cc.trigger_text, "
                "c.recorded_at, CASE "
                "WHEN c.state = 'intended' AND c.authority IN ('real_play', 'dm_correction') "
                "AND NOT c.predicts_subject_action THEN 'player_plan' "
                "WHEN c.authority IN ('real_play', 'dm_correction') THEN 'real_play' "
                "WHEN c.authority = 'npc_intention' THEN 'npc_plan' "
                "WHEN c.authority IN ('brainstorm', 'preparation') THEN 'dm_plan' "
                "WHEN c.state = 'intended' AND c.predicts_subject_action THEN 'player_plan' "
                "ELSE 'lore_fact' END, "
                "substring(convert_from(sr.raw_content, 'UTF8') "
                "from ss.start_offset + 1 for ss.end_offset - ss.start_offset), "
                "cs.superseding_claim_id, cs.reason, "
                "c.subject_entity_id, se.canonical_name "
                "FROM claims c "
                "JOIN claim_evidence evidence ON evidence.claim_id = c.id "
                "JOIN source_spans ss ON ss.id = evidence.source_span_id "
                "JOIN source_revisions sr ON sr.id = ss.source_revision_id "
                "JOIN claim_supersessions cs ON cs.superseded_claim_id = c.id "
                "LEFT JOIN entities se ON se.id = c.subject_entity_id "
                "LEFT JOIN claim_conditions cc ON cc.claim_id = c.id "
                "WHERE sr.source_document_id = %s "
                "ORDER BY c.id, ss.start_offset",
                (document_id,),
            ).fetchall()
        if row is None:
            return None
        result = _source_document_content_row(document_id, row)
        return result.model_copy(
            update={
                "canonical_claims": tuple(
                    SourceDocumentClaim(
                        claim_id=claim[0],
                        assertion_text=str(claim[1]),
                        state=str(claim[2]),
                        authority=str(claim[3]),
                        visibility=str(claim[4]),
                        conditional=bool(claim[5]),
                        condition_text=str(claim[6]) if claim[6] is not None else None,
                        recorded_at=claim[7],
                        projection=cast(ClaimProjection, str(claim[8])),
                        source_excerpt=str(claim[9]) if claim[9] is not None else None,
                        subject_entity_id=claim[10],
                        subject_entity_name=str(claim[11]) if claim[11] is not None else None,
                    )
                    for claim in claim_rows
                ),
                "claim_history": tuple(
                    SourceDocumentClaimHistory(
                        claim_id=claim[0],
                        assertion_text=str(claim[1]),
                        state=str(claim[2]),
                        authority=str(claim[3]),
                        visibility=str(claim[4]),
                        conditional=bool(claim[5]),
                        condition_text=str(claim[6]) if claim[6] is not None else None,
                        recorded_at=claim[7],
                        projection=cast(ClaimProjection, str(claim[8])),
                        source_excerpt=str(claim[9]) if claim[9] is not None else None,
                        superseded_by_claim_id=claim[10],
                        supersession_reason=str(claim[11]),
                        subject_entity_id=claim[12],
                        subject_entity_name=str(claim[13]) if claim[13] is not None else None,
                    )
                    for claim in history_rows
                ),
            }
        )


def _run_summary(status: str, receipt: ImportReceipt) -> ImportRunSummary:
    outcomes = Counter(item.outcome.value for item in receipt.observation.files)
    warnings = Counter(
        warning.value for item in receipt.observation.files for warning in item.warnings
    )
    return ImportRunSummary(
        import_run_id=receipt.import_run_id,
        root_identifier=receipt.root_identifier,
        snapshot_at=receipt.snapshot_at,
        importer_version=receipt.importer_version,
        parser_version=receipt.parser_version,
        path_policy_version=receipt.path_policy_version,
        status=status,
        admitted_file_count=receipt.observation.admitted_file_count,
        excluded_path_count=len(receipt.observation.excluded_paths_encountered),
        candidate_count=sum(len(item.candidate_ids) for item in receipt.observation.files),
        review_count=sum(len(item.review_ids) for item in receipt.observation.files),
        outcome_counts=dict(sorted(outcomes.items())),
        warning_counts=dict(sorted(warnings.items())),
    )


def _run_filters(query: ImportRunListQuery) -> tuple[str, tuple[Any, ...]]:
    clauses: list[str] = []
    parameters: list[Any] = []
    if query.status:
        clauses.append("ir.status = %s")
        parameters.append(query.status)
    if query.root_identifier:
        clauses.append("ir.receipt_json->>'root_identifier' = %s")
        parameters.append(query.root_identifier)
    return ("WHERE " + " AND ".join(clauses) if clauses else "", tuple(parameters))


def _candidate_visibility(requester: RequesterVisibility) -> tuple[str, tuple[Any, ...]]:
    if requester.role is RequesterRole.DM:
        return "", ()
    if requester.role is RequesterRole.PARTY:
        return "AND ic.visibility = %s", (Visibility.PARTY.value,)
    return "AND ic.visibility IN (%s, %s)", (Visibility.PARTY.value, Visibility.CHARACTER.value)


def _candidate_filters(query: CandidateListQuery) -> tuple[str, tuple[Any, ...]]:
    clauses: list[str] = []
    parameters: list[Any] = []
    visibility_sql, visibility_parameters = _candidate_visibility(query.requester)
    if visibility_sql:
        clauses.append(visibility_sql.removeprefix("AND "))
        parameters.extend(visibility_parameters)
    for column, value in (
        ("ic.first_seen_import_run_id", query.run_id),
        ("ic.status", query.status),
        ("ic.review_status", query.review_status),
        ("ic.state", query.state.value if query.state else None),
        ("ic.authority", query.authority.value if query.authority else None),
        ("ic.visibility", query.visibility.value if query.visibility else None),
    ):
        if value is not None:
            clauses.append(f"{column} = %s")
            parameters.append(value)
    evidence_clauses: list[str] = []
    if query.classification is not None:
        evidence_clauses.append("sr.classification = %s")
        parameters.append(query.classification.value)
    if query.source:
        evidence_clauses.append("coalesce(sr.original_path, sd.original_path) ILIKE %s")
        parameters.append(f"%{query.source}%")
    if evidence_clauses:
        clauses.append(
            "EXISTS (SELECT 1 FROM import_candidate_evidence ice "
            "JOIN source_revisions sr ON sr.id = ice.source_revision_id "
            "JOIN source_documents sd ON sd.id = ic.source_document_id "
            "WHERE ice.candidate_id = ic.id AND " + " AND ".join(evidence_clauses) + ")"
        )
    return ("WHERE " + " AND ".join(clauses) if clauses else "", tuple(parameters))


def _load_candidate(connection: Any, candidate_id: UUID) -> ImportCandidateReview | None:
    candidate = connection.execute(
        "SELECT id, source_document_id, first_seen_import_run_id, assertion_text, state::text, "
        "authority::text, visibility, is_conditional, predicts_subject_action, evidence_only, "
        "status, review_status, extractor_version, created_at, updated_at "
        "FROM import_candidates WHERE id = %s",
        (candidate_id,),
    ).fetchone()
    if candidate is None:
        return None
    evidence_rows = connection.execute(
        "SELECT sr.id, coalesce(sr.original_path, sd.original_path), sr.content_hash, "
        "sr.classification, ice.section_path, ice.start_offset, ice.end_offset, sr.raw_content, "
        "sr.frontmatter_json "
        "FROM import_candidate_evidence ice "
        "JOIN source_revisions sr ON sr.id = ice.source_revision_id "
        "JOIN source_documents sd ON sd.id = sr.source_document_id "
        "WHERE ice.candidate_id = %s ORDER BY sr.captured_at DESC, sr.id",
        (candidate_id,),
    ).fetchall()
    evidence = tuple(_candidate_evidence(row) for row in evidence_rows)
    extraction_rows = connection.execute(
        "SELECT id, subject, predicate, object_entity, assertion_text, supporting_excerpt, "
        "state, authority, visibility, confidence, extractor_version, source_segment_ids, "
        "subject_resolution "
        "FROM candidate_extractions WHERE extraction_run_id = ("
        "SELECT id FROM candidate_extraction_runs WHERE candidate_id = %s "
        "ORDER BY created_at DESC, id DESC LIMIT 1) ORDER BY created_at, id",
        (candidate_id,),
    ).fetchall()
    extractions = tuple(_candidate_extraction(row) for row in extraction_rows)
    run_row = connection.execute(
        "SELECT segments_json, coverage_json FROM candidate_extraction_runs "
        "WHERE candidate_id = %s ORDER BY created_at DESC, id DESC LIMIT 1",
        (candidate_id,),
    ).fetchone()
    extraction_segments = _candidate_extraction_segments(run_row)
    return ImportCandidateReview(
        candidate_id=candidate[0],
        source_document_id=candidate[1],
        first_seen_import_run_id=candidate[2],
        assertion_text=str(candidate[3]),
        state=ClaimState(str(candidate[4])),
        authority=CandidateAuthority(str(candidate[5])),
        visibility=Visibility(str(candidate[6])),
        conditional=bool(candidate[7]),
        predicts_subject_action=bool(candidate[8]),
        evidence_only=bool(candidate[9]),
        status=str(candidate[10]),
        review_status=str(candidate[11]),
        extractor_version=str(candidate[12]),
        created_at=candidate[13],
        updated_at=candidate[14],
        evidence=evidence,
        extractions=extractions,
        extraction_segments=extraction_segments,
    )


def _candidate_evidence(row: tuple[Any, ...]) -> CandidateEvidence:
    text = bytes(row[7]).decode("utf-8")
    start = int(row[5])
    end = int(row[6])
    if end > len(text):
        raise ValueError("candidate evidence span exceeds immutable source revision")
    frontmatter = dict(row[8]) if row[8] else {}
    mentions = tuple(
        mention
        for mention in frontmatter.get("mentions", [])
        if int(mention.get("start_offset", -1)) < end and int(mention.get("end_offset", -1)) > start
    )
    return CandidateEvidence(
        source_revision_id=row[0],
        source_path=str(row[1]),
        content_hash=str(row[2]),
        classification=ImportClassification(str(row[3])),
        section=str(row[4]),
        start_offset=start,
        end_offset=end,
        excerpt=text[start:end],
        in_game_date=frontmatter.get("in_game_date"),
        mentions=mentions,
    )


def _candidate_extraction(row: tuple[Any, ...]) -> CandidateExtractionReview:
    from decimal import Decimal as _Decimal

    return CandidateExtractionReview(
        extraction_id=row[0],
        subject=str(row[1]),
        subject_resolution=SubjectResolution(str(row[12])),
        predicate=str(row[2]) if row[2] is not None else None,
        object_entity=str(row[3]) if row[3] is not None else None,
        assertion_text=str(row[4]),
        supporting_excerpt=str(row[5]),
        state=ClaimState(str(row[6])),
        authority=CandidateAuthority(str(row[7])),
        visibility=Visibility(str(row[8])),
        confidence=_Decimal(str(row[9])),
        extractor_version=str(row[10]),
        source_segment_ids=tuple(str(item) for item in row[11]),
    )


def _candidate_extraction_segments(
    row: tuple[Any, ...] | None,
) -> tuple[CandidateExtractionSegmentReview, ...]:
    if row is None:
        return ()
    segments = {str(item["segment_id"]): item for item in (row[0] or [])}
    coverage = {str(item["segment_id"]): item for item in (row[1] or [])}
    return tuple(
        CandidateExtractionSegmentReview(
            segment_id=segment_id,
            text=str(segment["text"]),
            start_offset=int(segment["start_offset"]),
            end_offset=int(segment["end_offset"]),
            disposition=str(coverage.get(segment_id, {}).get("disposition", "unaccounted")),
            claim_indexes=tuple(
                int(index) for index in coverage.get(segment_id, {}).get("claim_indexes", [])
            ),
        )
        for segment_id, segment in segments.items()
    )


_REVIEW_SOURCE_LATERAL = """
LEFT JOIN LATERAL (
    SELECT coalesce(sr.original_path, sd.original_path) AS source_path,
           sr.classification
    FROM source_documents sd
    LEFT JOIN source_revisions sr ON sr.source_document_id = sd.id
    WHERE sd.id = ri.subject_id
    ORDER BY sr.captured_at DESC NULLS LAST, sr.id DESC
    LIMIT 1
) source ON true
"""


def _review_filters(query: ReviewItemListQuery) -> tuple[str, tuple[Any, ...]]:
    clauses = ["ri.opened_by_import_run_id IS NOT NULL"]
    parameters: list[Any] = []
    if query.status is None:
        clauses.append("ri.status <> 'superseded'")
    for column, value in (
        ("ri.opened_by_import_run_id", query.run_id),
        ("ri.kind", query.kind),
        ("ri.status", query.status),
    ):
        if value is not None:
            clauses.append(f"{column} = %s")
            parameters.append(value)
    if query.classification is not None:
        clauses.append("coalesce(ri.details->>'classification', source.classification) = %s")
        parameters.append(query.classification.value)
    candidate_clauses: list[str] = []
    for column, value in (
        ("ic.state", query.state.value if query.state else None),
        ("ic.authority", query.authority.value if query.authority else None),
        ("ic.visibility", query.visibility.value if query.visibility else None),
    ):
        if value is not None:
            candidate_clauses.append(f"{column} = %s")
            parameters.append(value)
    if candidate_clauses:
        clauses.append(
            "EXISTS (SELECT 1 FROM import_candidates ic "
            "WHERE ic.source_document_id = ri.subject_id AND "
            + " AND ".join(candidate_clauses)
            + ")"
        )
    if query.source:
        clauses.append("coalesce(ri.details->>'path', source.source_path) ILIKE %s")
        parameters.append(f"%{query.source}%")
    return "WHERE " + " AND ".join(clauses), tuple(parameters)


_SOURCE_DOCUMENTS_SQL = """
SELECT
    sd.id,
    sdp.normalized_path,
    COALESCE(latest.classification, sd.source_kind),
    COALESCE(cand.candidate_count, 0),
    COALESCE(ext.extraction_count, 0),
    COALESCE(cand.candidate_count, 0),
    (sdp.missing_scans > 0),
    latest.frontmatter_json
FROM source_documents sd
JOIN source_document_paths sdp
    ON sdp.source_document_id = sd.id AND sdp.is_current AND sdp.connector = sd.connector
LEFT JOIN LATERAL (
    SELECT sr.classification, sr.frontmatter_json
    FROM source_revisions sr
    WHERE sr.source_document_id = sd.id
    ORDER BY sr.captured_at DESC, sr.id DESC
    LIMIT 1
) latest ON true
LEFT JOIN (
    SELECT ic.source_document_id, count(*)::int AS candidate_count
    FROM import_candidates ic
    WHERE ic.status = 'active' AND ic.review_status IN ('pending', 'proposed')
    GROUP BY ic.source_document_id
) cand ON cand.source_document_id = sd.id
LEFT JOIN (
    SELECT ic.source_document_id, count(*)::int AS extraction_count
    FROM import_candidates ic
    JOIN LATERAL (
        SELECT id FROM candidate_extraction_runs cer
        WHERE cer.candidate_id = ic.id
        ORDER BY cer.created_at DESC, cer.id DESC
        LIMIT 1
    ) latest_run ON true
    JOIN candidate_extractions ce ON ce.extraction_run_id = latest_run.id
    WHERE ic.status = 'active'
    GROUP BY ic.source_document_id
) ext ON ext.source_document_id = sd.id
LEFT JOIN (
    SELECT ri.subject_id, count(*)::int AS review_count
    FROM review_items ri
    WHERE ri.status = 'open' AND ri.subject_type = 'source_document'
    GROUP BY ri.subject_id
) rev ON rev.subject_id = sd.id
ORDER BY sdp.normalized_path
"""


def _source_document_row(row: tuple[Any, ...]) -> SourceDocumentSummary:
    frontmatter = dict(row[7]) if row[7] else {}
    return SourceDocumentSummary(
        document_id=row[0],
        path=str(row[1]),
        classification=ImportClassification(str(row[2])),
        candidate_count=int(row[3]),
        extraction_count=int(row[4]),
        open_review_count=int(row[5]),
        missing_source=bool(row[6]),
        document_type=frontmatter.get("type"),
        title=frontmatter.get("name"),
        session_date=frontmatter.get("session_date"),
        capture_mode=frontmatter.get("capture_mode"),
    )


_SOURCE_DOCUMENT_CONTENT_SQL = """
SELECT sdp.normalized_path, sr.raw_content, sr.id, sr.frontmatter_json, sd.external_id
FROM source_documents sd
JOIN source_document_paths sdp
    ON sdp.source_document_id = sd.id AND sdp.is_current AND sdp.connector = sd.connector
LEFT JOIN LATERAL (
    SELECT sr2.id, sr2.raw_content, sr2.frontmatter_json
    FROM source_revisions sr2
    WHERE sr2.source_document_id = sd.id
    ORDER BY sr2.captured_at DESC, sr2.id DESC
    LIMIT 1
) sr ON true
WHERE sd.id = %s
"""


def _source_document_content_row(document_id: UUID, row: tuple[Any, ...]) -> SourceDocumentContent:
    raw_content = row[1]
    content = bytes(raw_content).decode("utf-8") if raw_content is not None else ""
    frontmatter = dict(row[3]) if row[3] else {}
    return SourceDocumentContent(
        document_id=document_id,
        path=str(row[0]),
        source_revision_id=row[2],
        content=content,
        document_type=frontmatter.get("type"),
        title=frontmatter.get("name"),
        session_date=frontmatter.get("session_date"),
        in_game_date=frontmatter.get("in_game_date"),
        capture_mode=frontmatter.get("capture_mode"),
        capture_id=row[4],
        mentions=tuple(frontmatter.get("mentions", [])),
        referenced_claims=tuple(
            str(value)
            for value in frontmatter.get("referenced_claims", [])
            if isinstance(value, (str, int))
        ),
    )
