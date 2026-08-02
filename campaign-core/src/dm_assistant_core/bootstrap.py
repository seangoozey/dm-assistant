"""Process entry point: migrate, then serve Campaign Core."""

import uvicorn

from dm_assistant_core.adapters.postgres.migrate import run_migrations
from dm_assistant_core.config import get_settings


def main() -> None:
    settings = get_settings()
    if settings.run_migrations:
        run_migrations(settings.database_dsn)
    uvicorn.run(
        "dm_assistant_core.api.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    main()

