"""PostgreSQL persistence for the migration-closure audit command."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb


def _counts(connection: psycopg.Connection[Any], table: str, column: str) -> dict[str, int]:
    rows = connection.execute(
        f"SELECT {column}::text, count(*)::int FROM {table} GROUP BY {column} ORDER BY {column}"
    ).fetchall()
    return {str(row[0]): int(row[1]) for row in rows}


def build_report(connection: psycopg.Connection[Any]) -> dict[str, Any]:
    scalar = connection.execute(
        "SELECT "
        "(SELECT count(*)::int FROM source_documents), "
        "(SELECT count(*)::int FROM source_revisions), "
        "(SELECT count(*)::int FROM claims), "
        "(SELECT count(*)::int FROM claims c WHERE NOT EXISTS "
        " (SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id=c.id)), "
        "(SELECT count(*)::int FROM claims c WHERE NOT EXISTS "
        " (SELECT 1 FROM claim_evidence ce WHERE ce.claim_id=c.id)), "
        "(SELECT count(*)::int FROM source_review_dispositions)"
    ).fetchone()
    assert scalar is not None
    candidates = _counts(connection, "import_candidates", "review_status")
    reviews = _counts(connection, "review_items", "status")
    blockers = {
        "nonterminal_candidates": sum(candidates.get(key, 0) for key in ("pending", "proposed")),
        "deferred_candidates": candidates.get("deferred", 0),
        "open_source_reviews": reviews.get("open", 0),
        "claims_without_evidence": int(scalar[4]),
    }
    return {
        "migration_key": "starfall-live-markdown-v0.1",
        "source_documents": int(scalar[0]),
        "source_revisions": int(scalar[1]),
        "candidate_review_statuses": candidates,
        "source_review_statuses": reviews,
        "source_review_dispositions": int(scalar[5]),
        "canonical_claims_total": int(scalar[2]),
        "canonical_claims_current": int(scalar[3]),
        "blockers": blockers,
        "closed": all(value == 0 for value in blockers.values()),
    }


def audit_migration(dsn: str, *, record: bool) -> dict[str, Any]:
    with psycopg.connect(dsn) as connection:
        report = build_report(connection)
        encoded = json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
        report_hash = hashlib.sha256(encoded).hexdigest()
        result = {**report, "report_hash": report_hash}
        if record:
            if not report["closed"]:
                raise RuntimeError("migration closure has blockers")
            report_id = uuid4()
            created_at = datetime.now(UTC)
            existing = connection.execute(
                "SELECT id, report_hash, created_at FROM migration_closure_reports "
                "WHERE migration_key=%s",
                (report["migration_key"],),
            ).fetchone()
            if existing is None:
                connection.execute(
                    "INSERT INTO migration_closure_reports"
                    "(id,migration_key,report_hash,report_json,created_at) VALUES (%s,%s,%s,%s,%s)",
                    (report_id, report["migration_key"], report_hash, Jsonb(report), created_at),
                )
            else:
                report_id, prior_hash, created_at = existing
                if str(prior_hash) != report_hash:
                    raise RuntimeError("recorded migration closure differs from current audit")
            result.update({"report_id": str(report_id), "recorded_at": created_at.isoformat()})
    return result
