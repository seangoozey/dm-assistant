"""Read-only SQL smoke check against the local development PostgreSQL container.

Run using Campaign Core's Python. Never prints assertions or credentials.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "campaign-core/src"))

from dm_assistant_core.adapters.postgres.retrieval import (
    PostgresRetrievalRepository,
    _SHARED_EVIDENCE_SQL,
)
from dm_assistant_core.domain.retrieval import RetrievalQuery

database = MagicMock()
connection = database.connection.return_value.__enter__.return_value
connection.execute.return_value.fetchall.return_value = []
PostgresRetrievalRepository(database).current_records(
    RetrievalQuery(question="validation", requester_visibility={"role": "dm"}),
    (str(uuid4()),))
sql = connection.execute.call_args.args[0]
sql = sql.replace("%s", "ARRAY(SELECT id FROM claims ORDER BY id LIMIT 5)")
statement = (
    "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY; SELECT count(*) AS loaded_records, "
    "count(evidence_binding) AS records_with_evidence_binding FROM (" + sql + ") verified; "
    "SELECT count(*) AS shared_evidence_links FROM ("
    + _SHARED_EVIDENCE_SQL.replace(
        "%s", "ARRAY(SELECT id FROM claims ORDER BY id LIMIT 100)")
    + ") links; ROLLBACK;"
)
result = subprocess.run([
    "docker", "exec", "-i", "dm-assistant-campaign-db-1", "psql", "-X",
    "-U", "campaign_owner", "-d", "campaign", "-v", "ON_ERROR_STOP=1",
], input=statement, text=True, capture_output=True, check=False)
print(result.stdout)
if result.returncode:
    print(result.stderr)
raise SystemExit(result.returncode)
