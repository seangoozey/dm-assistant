"""PostgreSQL read adapter for import receipts, candidates, and reviews."""

from __future__ import annotations

from collections import Counter
from typing import Any
from uuid import UUID

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.import_reviews import (
    CandidateEvidence,
    CandidateListQuery,
    ImportCandidatePage,
    ImportCandidateReview,
    ImportReviewItem,
    ImportReviewItemPage,
    ImportRunDetail,
    ImportRunListQuery,
    ImportRunPage,
    ImportRunSummary,
    ReviewItemListQuery,
)
from dm_assistant_core.domain import ClaimState, RequesterRole, RequesterVisibility, Visibility
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

    def list_candidates(self, query: CandidateListQuery) -> ImportCandidatePage:
        where, parameters = _candidate_filters(query)
        with self._database.connection() as connection:
            total_row = connection.execute(
                f"SELECT count(*) FROM import_candidates ic {where}", parameters
            ).fetchone()
            id_rows = connection.execute(
                "SELECT ic.id FROM import_candidates ic "
                f"{where} ORDER BY ic.created_at, ic.id LIMIT %s OFFSET %s",
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
        "sr.classification, ice.section_path, ice.start_offset, ice.end_offset, sr.raw_content "
        "FROM import_candidate_evidence ice "
        "JOIN source_revisions sr ON sr.id = ice.source_revision_id "
        "JOIN source_documents sd ON sd.id = sr.source_document_id "
        "WHERE ice.candidate_id = %s ORDER BY sr.captured_at DESC, sr.id",
        (candidate_id,),
    ).fetchall()
    evidence = tuple(_candidate_evidence(row) for row in evidence_rows)
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
    )


def _candidate_evidence(row: tuple[Any, ...]) -> CandidateEvidence:
    text = bytes(row[7]).decode("utf-8")
    start = int(row[5])
    end = int(row[6])
    if end > len(text):
        raise ValueError("candidate evidence span exceeds immutable source revision")
    return CandidateEvidence(
        source_revision_id=row[0],
        source_path=str(row[1]),
        content_hash=str(row[2]),
        classification=ImportClassification(str(row[3])),
        section=str(row[4]),
        start_offset=start,
        end_offset=end,
        excerpt=text[start:end],
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
