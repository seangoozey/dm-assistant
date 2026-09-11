"""Verify and immutably record migration closure from aggregate database evidence."""

from __future__ import annotations

import argparse
import json
import os

from dm_assistant_core.adapters.postgres.migration_closure import audit_migration


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    dsn = os.environ["CAMPAIGN_DATABASE_URL"]
    try:
        result = audit_migration(dsn, record=args.record)
    except RuntimeError as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
