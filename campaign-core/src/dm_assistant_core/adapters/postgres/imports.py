"""Transactional PostgreSQL persistence for read-only Markdown scans."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import PurePosixPath
from typing import Any, cast
from uuid import UUID, uuid4

from psycopg import Connection
from psycopg.types.json import Jsonb

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.importer import (
    ImportFileOutcome,
    ImportObservationReceipt,
    ImportOutcome,
    ImportReceipt,
    ImportWarning,
    MarkdownScanBatch,
    ScannedSource,
)
from dm_assistant_core.importer.models import ImportRejectedError

REVIEW_WARNINGS = {
    ImportWarning.UNRESOLVED_LINK,
    ImportWarning.INVALID_FRONTMATTER,
    ImportWarning.MISSING_FRONTMATTER,
    ImportWarning.INVALID_UTF8,
    ImportWarning.CLASSIFICATION_CONFLICT,
}
WORD = re.compile(r"[a-z0-9]+")


class PostgresMarkdownImportRepository:
    """Persist evidence and candidates without writing canonical campaign records."""

    def __init__(self, database: PostgresDatabase, missing_confirmation_threshold: int = 1) -> None:
        if missing_confirmation_threshold < 1:
            raise ValueError("missing confirmation threshold must be at least one")
        self._database = database
        self._missing_confirmation_threshold = missing_confirmation_threshold

    def ingest(self, batch: MarkdownScanBatch) -> ImportReceipt:
        self._validate_batch(batch)
        with self._database.connection() as connection:
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (batch.idempotency_key,),
            )
            prior = connection.execute(
                "SELECT receipt_json FROM import_runs WHERE idempotency_key = %s",
                (batch.idempotency_key,),
            ).fetchone()
            if prior is not None:
                receipt = ImportReceipt.model_validate(prior[0])
                return receipt.model_copy(update={"idempotent_replay": True})
            return self._ingest_new(connection, batch)

    @staticmethod
    def _validate_batch(batch: MarkdownScanBatch) -> None:
        paths = [source.path for source in batch.files]
        if paths != sorted(paths, key=str.casefold) or len(paths) != len(set(paths)):
            raise ImportRejectedError("scan paths must be unique and deterministically sorted")
        reextract_paths = list(batch.reextract_paths)
        if reextract_paths != sorted(reextract_paths, key=str.casefold) or len(
            reextract_paths
        ) != len(set(reextract_paths)):
            raise ImportRejectedError(
                "re-extraction paths must be unique and deterministically sorted"
            )
        missing_reextract_paths = set(reextract_paths) - set(paths)
        if missing_reextract_paths:
            missing = ", ".join(sorted(missing_reextract_paths, key=str.casefold))
            raise ImportRejectedError(
                f"re-extraction paths must be present in the full scan: {missing}"
            )
        for source in batch.files:
            from hashlib import sha256

            if sha256(source.content).hexdigest() != source.content_hash:
                raise ImportRejectedError(f"content hash mismatch for {source.path}")
            path = PurePosixPath(source.path)
            if path.is_absolute() or ".." in path.parts or not _path_is_admitted(path):
                raise ImportRejectedError(
                    f"submitted path is outside connector policy: {source.path}"
                )

    def _ingest_new(
        self,
        connection: Connection[Any],
        batch: MarkdownScanBatch,
    ) -> ImportReceipt:
        run_id = uuid4()
        connector = f"markdown:{batch.root_identifier}"
        present_paths = {source.path for source in batch.files}
        outcomes: list[ImportFileOutcome] = []
        pending_reviews: list[tuple[UUID, str, UUID, dict[str, Any]]] = []

        for source in batch.files:
            outcome, review_kind = self._ingest_source(
                connection,
                run_id,
                connector,
                source,
                present_paths,
                batch,
            )
            outcomes.append(outcome)
            for warning in source.warnings:
                if warning in REVIEW_WARNINGS:
                    subject_id = cast(UUID, outcome.source_document_id)
                    details = {"path": source.path, "warning": warning.value}
                    if not self._open_review_exists(
                        connection, "import_warning", subject_id, details
                    ):
                        pending_reviews.append(
                            (uuid4(), "import_warning", subject_id, details)
                        )
            if review_kind is not None:
                subject_id = cast(UUID, outcome.source_document_id)
                details = {
                    "path": source.path,
                    "classification": source.classification.value,
                    "outcome": (
                        outcome.outcome.value
                        if review_kind == "possible_move"
                        else source.proposed_outcome.value
                    ),
                }
                if not self._open_review_exists(
                    connection, review_kind, subject_id, details
                ):
                    pending_reviews.append((uuid4(), review_kind, subject_id, details))

        outcomes.extend(
            self._record_missing_sources(
                connection,
                connector,
                present_paths,
                batch.snapshot_at,
                pending_reviews,
            )
        )
        review_ids_by_subject: dict[UUID, list[UUID]] = {}
        for review_id, _kind, subject_id, _details in pending_reviews:
            review_ids_by_subject.setdefault(subject_id, []).append(review_id)
        outcomes = [
            outcome.model_copy(
                update={
                    "review_ids": tuple(
                        review_ids_by_subject.get(cast(UUID, outcome.source_document_id), [])
                    )
                }
            )
            for outcome in outcomes
        ]
        observation = ImportObservationReceipt(
            admitted_file_count=len(batch.files),
            excluded_paths_encountered=batch.excluded_paths_encountered,
            files=tuple(outcomes),
        )
        receipt = ImportReceipt(
            import_run_id=run_id,
            idempotency_key=batch.idempotency_key,
            root_identifier=batch.root_identifier,
            snapshot_at=batch.snapshot_at,
            importer_version=batch.importer_version,
            parser_version=batch.parser_version,
            path_policy_version=batch.path_policy_version,
            outcome="completed",
            observation=observation,
            idempotent_replay=False,
        )
        connection.execute(
            "INSERT INTO import_runs "
            "(id, connector, started_at, finished_at, importer_version, idempotency_key, "
            "status, receipt_json) VALUES (%s, %s, %s, %s, %s, %s, 'completed', %s)",
            (
                run_id,
                connector,
                batch.snapshot_at,
                batch.snapshot_at,
                batch.importer_version,
                batch.idempotency_key,
                Jsonb(receipt.model_dump(mode="json")),
            ),
        )
        for outcome, source in zip(outcomes[: len(batch.files)], batch.files, strict=True):
            connection.execute(
                "INSERT INTO import_observations "
                "(id, import_run_id, source_document_id, source_revision_id, classification, "
                "outcome, warning_json) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    uuid4(),
                    run_id,
                    outcome.source_document_id,
                    outcome.source_revision_id,
                    source.classification.value,
                    outcome.outcome.value,
                    Jsonb([warning.value for warning in source.warnings]),
                ),
            )
        for outcome in outcomes[len(batch.files) :]:
            connection.execute(
                "INSERT INTO import_observations "
                "(id, import_run_id, source_document_id, classification, outcome, warning_json) "
                "VALUES (%s, %s, %s, 'missing_source', %s, '[]'::jsonb)",
                (uuid4(), run_id, outcome.source_document_id, outcome.outcome.value),
            )
        for review_id, kind, subject_id, details in pending_reviews:
            connection.execute(
                "INSERT INTO review_items "
                "(id, kind, status, subject_type, subject_id, details, "
                "opened_by_import_run_id, created_at, updated_at) "
                "VALUES (%s, %s, 'open', 'source_document', %s, %s, %s, %s, %s)",
                (
                    review_id,
                    kind,
                    subject_id,
                    Jsonb(details),
                    run_id,
                    batch.snapshot_at,
                    batch.snapshot_at,
                ),
            )
        return receipt

    @staticmethod
    def _open_review_exists(
        connection: Connection[Any],
        kind: str,
        subject_id: UUID,
        details: dict[str, Any],
    ) -> bool:
        row = connection.execute(
            "SELECT 1 FROM review_items "
            "WHERE kind = %s AND status = 'open' AND subject_type = 'source_document' "
            "AND subject_id = %s AND details = %s LIMIT 1",
            (kind, subject_id, Jsonb(details)),
        ).fetchone()
        return row is not None

    def _ingest_source(
        self,
        connection: Connection[Any],
        run_id: UUID,
        connector: str,
        source: ScannedSource,
        present_paths: set[str],
        batch: MarkdownScanBatch,
    ) -> tuple[ImportFileOutcome, str | None]:
        document_id, identity_kind = self._resolve_document(
            connection, connector, source, present_paths
        )
        new_document = document_id is None or identity_kind == "possible_move"
        possible_move_target = document_id if identity_kind == "possible_move" else None
        if new_document:
            document_id = uuid4()
            connection.execute(
                "INSERT INTO source_documents "
                "(id, source_kind, connector, original_path, external_id, first_seen_at) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    document_id,
                    source.classification.value,
                    connector,
                    source.path,
                    source.external_id,
                    batch.snapshot_at,
                ),
            )
        assert document_id is not None

        current_path = connection.execute(
            "SELECT normalized_path FROM source_document_paths "
            "WHERE source_document_id = %s AND is_current FOR UPDATE",
            (document_id,),
        ).fetchone()
        moved = current_path is not None and current_path[0] != source.path
        if moved:
            connection.execute(
                "UPDATE source_document_paths SET is_current = false, last_seen_at = %s "
                "WHERE source_document_id = %s AND is_current",
                (batch.snapshot_at, document_id),
            )
        connection.execute(
            "INSERT INTO source_document_paths "
            "(source_document_id, connector, normalized_path, first_seen_at, last_seen_at, "
            "is_current, missing_scans) VALUES (%s, %s, %s, %s, %s, true, 0) "
            "ON CONFLICT (source_document_id, normalized_path) DO UPDATE SET "
            "last_seen_at = EXCLUDED.last_seen_at, is_current = true, missing_scans = 0, "
            "missing_reviewed_at = NULL",
            (
                document_id,
                connector,
                source.path,
                batch.snapshot_at,
                batch.snapshot_at,
            ),
        )
        existing_revision = connection.execute(
            "SELECT id FROM source_revisions "
            "WHERE source_document_id = %s AND content_hash = %s FOR UPDATE",
            (document_id, source.content_hash),
        ).fetchone()
        revision_id: UUID | None
        candidate_ids: list[UUID] = []
        if existing_revision is not None:
            revision_id = existing_revision[0]
            extraction_exists = connection.execute(
                "SELECT 1 FROM source_extractions "
                "WHERE source_revision_id = %s AND parser_version = %s",
                (revision_id, batch.parser_version),
            ).fetchone()
            if extraction_exists is not None or source.path not in batch.reextract_paths:
                candidate_ids = [
                    row[0]
                    for row in connection.execute(
                        "SELECT id FROM import_candidates "
                        "WHERE source_document_id = %s AND status = 'active' ORDER BY id",
                        (document_id,),
                    ).fetchall()
                ]
                outcome = ImportOutcome.MOVED if moved else ImportOutcome.UNCHANGED
            else:
                candidate_ids = self._persist_extraction(
                    connection,
                    run_id=run_id,
                    document_id=document_id,
                    revision_id=revision_id,
                    source=source,
                    batch=batch,
                    reconcile_prior=True,
                )
                outcome = ImportOutcome.MOVED if moved else ImportOutcome.REEXTRACTED
        else:
            revision_id = uuid4()
            connection.execute(
                "INSERT INTO source_revisions "
                "(id, source_document_id, content_hash, raw_content, source_time, "
                "importer_version, captured_at, original_path, filesystem_modified_at, "
                "discovered_at, parser_version, path_policy_version, frontmatter_json, "
                "classification) VALUES "
                "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    revision_id,
                    document_id,
                    source.content_hash,
                    source.content,
                    source.filesystem_modified_at,
                    batch.importer_version,
                    batch.snapshot_at,
                    source.path,
                    source.filesystem_modified_at,
                    batch.snapshot_at,
                    batch.parser_version,
                    batch.path_policy_version,
                    Jsonb(source.frontmatter),
                    source.classification.value,
                ),
            )
            candidate_ids = self._persist_extraction(
                connection,
                run_id=run_id,
                document_id=document_id,
                revision_id=revision_id,
                source=source,
                batch=batch,
                reconcile_prior=not new_document,
            )
            if identity_kind == "possible_move":
                outcome = ImportOutcome.POSSIBLE_MOVE
            elif new_document:
                outcome = source.proposed_outcome
            else:
                outcome = ImportOutcome.CHANGED

        review_kind: str | None = None
        if outcome is ImportOutcome.POSSIBLE_MOVE:
            review_kind = "possible_move"
        elif source.classification.value == "quarantine":
            review_kind = "import_quarantine"
        elif source.proposed_outcome is ImportOutcome.REVIEW_REQUIRED:
            review_kind = "import_review"
        details_warning = list(source.warnings)
        if possible_move_target is not None:
            details_warning.append(ImportWarning.POSSIBLE_MOVE_REVIEW)
        return (
            ImportFileOutcome(
                path=source.path,
                outcome=outcome,
                content_hash=source.content_hash,
                source_document_id=document_id,
                source_revision_id=revision_id,
                candidate_ids=tuple(candidate_ids),
                warnings=tuple(details_warning),
            ),
            review_kind,
        )

    @staticmethod
    def _persist_extraction(
        connection: Connection[Any],
        *,
        run_id: UUID,
        document_id: UUID,
        revision_id: UUID,
        source: ScannedSource,
        batch: MarkdownScanBatch,
        reconcile_prior: bool,
    ) -> list[UUID]:
        candidate_ids: list[UUID] = []
        for candidate in source.candidates:
            candidate_id = uuid4()
            row = connection.execute(
                "INSERT INTO import_candidates "
                "(id, source_document_id, fingerprint, assertion_text, state, authority, "
                "visibility, is_conditional, predicts_subject_action, evidence_only, "
                "status, extractor_version, first_seen_import_run_id, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active', %s, %s, %s, %s) "
                "ON CONFLICT (source_document_id, fingerprint) DO UPDATE SET "
                "status = 'active', updated_at = EXCLUDED.updated_at RETURNING id",
                (
                    candidate_id,
                    document_id,
                    candidate.fingerprint,
                    candidate.assertion_text,
                    candidate.state.value,
                    candidate.authority.value,
                    candidate.visibility.value,
                    candidate.conditional,
                    candidate.predicts_pc_action,
                    candidate.evidence_only,
                    candidate.extractor_version,
                    run_id,
                    batch.snapshot_at,
                    batch.snapshot_at,
                ),
            ).fetchone()
            assert row is not None
            candidate_id = row[0]
            candidate_ids.append(candidate_id)
            connection.execute(
                "INSERT INTO import_candidate_evidence "
                "(candidate_id, source_revision_id, section_path, start_offset, end_offset) "
                "VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (
                    candidate_id,
                    revision_id,
                    candidate.section,
                    candidate.start_offset,
                    candidate.end_offset,
                ),
            )
        if reconcile_prior:
            connection.execute(
                "UPDATE import_candidates SET status = 'source_removed', updated_at = %s "
                "WHERE source_document_id = %s AND status = 'active' "
                "AND NOT (id = ANY(%s::uuid[]))",
                (batch.snapshot_at, document_id, candidate_ids),
            )
        connection.execute(
            "INSERT INTO source_extractions "
            "(source_revision_id, parser_version, import_run_id, extracted_at) "
            "VALUES (%s, %s, %s, %s)",
            (revision_id, batch.parser_version, run_id, batch.snapshot_at),
        )
        return candidate_ids

    @staticmethod
    def _resolve_document(
        connection: Connection[Any],
        connector: str,
        source: ScannedSource,
        present_paths: set[str],
    ) -> tuple[UUID | None, str]:
        if source.external_id:
            row = connection.execute(
                "SELECT id FROM source_documents WHERE connector = %s AND external_id = %s",
                (connector, source.external_id),
            ).fetchone()
            if row is not None:
                return row[0], "external_id"
        row = connection.execute(
            "SELECT source_document_id FROM source_document_paths "
            "WHERE connector = %s AND normalized_path = %s",
            (connector, source.path),
        ).fetchone()
        if row is not None:
            return row[0], "path"
        exact_rows = connection.execute(
            "SELECT DISTINCT sr.source_document_id, sp.normalized_path "
            "FROM source_revisions sr "
            "JOIN source_documents sd ON sd.id = sr.source_document_id "
            "JOIN source_document_paths sp ON sp.source_document_id = sd.id AND sp.is_current "
            "WHERE sd.connector = %s AND sr.content_hash = %s",
            (connector, source.content_hash),
        ).fetchall()
        absent_exact = [row for row in exact_rows if row[1] not in present_paths]
        if len(absent_exact) == 1:
            return absent_exact[0][0], "exact_hash"
        if source.canonical_name:
            candidates = connection.execute(
                "SELECT DISTINCT ON (sd.id) sd.id, sp.normalized_path, sr.raw_content "
                "FROM source_documents sd "
                "JOIN source_document_paths sp ON sp.source_document_id = sd.id AND sp.is_current "
                "JOIN source_revisions sr ON sr.source_document_id = sd.id "
                "WHERE sd.connector = %s AND sr.frontmatter_json->>'name' = %s "
                "ORDER BY sd.id, sr.captured_at DESC",
                (connector, source.canonical_name),
            ).fetchall()
            likely = [
                row
                for row in candidates
                if row[1] not in present_paths and _content_overlap(row[2], source.content) >= 0.75
            ]
            if len(likely) == 1:
                return likely[0][0], "possible_move"
        return None, "new"

    def _record_missing_sources(
        self,
        connection: Connection[Any],
        connector: str,
        present_paths: set[str],
        observed_at: Any,
        pending_reviews: list[tuple[UUID, str, UUID, dict[str, Any]]],
    ) -> list[ImportFileOutcome]:
        rows = connection.execute(
            "SELECT source_document_id, normalized_path, missing_scans, missing_reviewed_at "
            "FROM source_document_paths WHERE connector = %s AND is_current FOR UPDATE",
            (connector,),
        ).fetchall()
        outcomes: list[ImportFileOutcome] = []
        for document_id, path, missing_scans, reviewed_at in rows:
            if path in present_paths or not _path_is_admitted(PurePosixPath(path)):
                continue
            new_count = int(missing_scans) + 1
            connection.execute(
                "UPDATE source_document_paths SET missing_scans = %s, last_seen_at = last_seen_at "
                "WHERE source_document_id = %s AND normalized_path = %s",
                (new_count, document_id, path),
            )
            if new_count < self._missing_confirmation_threshold:
                continue
            review_ids: tuple[UUID, ...] = ()
            if reviewed_at is None:
                review_id = uuid4()
                review_ids = (review_id,)
                pending_reviews.append(
                    (
                        review_id,
                        "missing_source",
                        document_id,
                        {"path": path, "missing_scans": new_count},
                    )
                )
                connection.execute(
                    "UPDATE source_document_paths SET missing_reviewed_at = %s "
                    "WHERE source_document_id = %s AND normalized_path = %s",
                    (observed_at, document_id, path),
                )
            outcomes.append(
                ImportFileOutcome(
                    path=path,
                    outcome=ImportOutcome.MISSING_SOURCE,
                    source_document_id=document_id,
                    review_ids=review_ids,
                )
            )
        return outcomes


def _path_is_admitted(path: PurePosixPath) -> bool:
    return bool(
        path.parts
        and path.parts[0] in {
            "encounters",
            "gm",
            "handouts",
            "locations",
            "lore",
            "npcs",
            "pcs",
            "sessions",
            "templates",
        }
        and path != PurePosixPath("gm/location-migration-inventory.md")
        and not (len(path.parts) >= 2 and path.parts[:2] == ("gm", "location-evidence"))
    )


def _content_overlap(prior: bytes, current: bytes) -> float:
    prior_words = WORD.findall(prior.decode("utf-8", errors="ignore").casefold())
    current_words = WORD.findall(current.decode("utf-8", errors="ignore").casefold())
    return SequenceMatcher(None, prior_words, current_words, autojunk=False).ratio()
