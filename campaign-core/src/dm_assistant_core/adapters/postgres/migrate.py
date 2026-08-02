"""Forward-only, hash-verified PostgreSQL migration runner."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import psycopg


@dataclass(frozen=True)
class Migration:
    version: str
    path: Path
    checksum: str
    sql: str


def load_migrations() -> tuple[Migration, ...]:
    migration_root = Path(__file__).with_name("migrations")
    migrations: list[Migration] = []
    for path in sorted(migration_root.glob("*.sql")):
        sql = path.read_text(encoding="utf-8")
        migrations.append(
            Migration(
                version=path.stem,
                path=path,
                checksum=sha256(sql.encode("utf-8")).hexdigest(),
                sql=sql,
            )
        )
    if not migrations:
        raise RuntimeError("no Campaign Core migrations found")
    return tuple(migrations)


def run_migrations(dsn: str) -> tuple[str, ...]:
    """Apply every pending migration transactionally under an advisory lock."""

    applied_now: list[str] = []
    with psycopg.connect(dsn) as connection:
        connection.execute("SELECT pg_advisory_xact_lock(248774357)")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS campaign_schema_migrations (
                version text PRIMARY KEY,
                checksum text NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        applied: dict[str, str] = dict(
            connection.execute(
                "SELECT version, checksum FROM campaign_schema_migrations"
            ).fetchall()
        )
        for migration in load_migrations():
            prior_checksum = applied.get(migration.version)
            if prior_checksum is not None:
                if prior_checksum != migration.checksum:
                    raise RuntimeError(
                        f"applied migration {migration.version} has a checksum mismatch"
                    )
                continue
            connection.execute(migration.sql, prepare=False)
            connection.execute(
                "INSERT INTO campaign_schema_migrations (version, checksum) VALUES (%s, %s)",
                (migration.version, migration.checksum),
            )
            applied_now.append(migration.version)
    return tuple(applied_now)
