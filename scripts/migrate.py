"""Plain-SQL migration runner — no Alembic, no autogeneration.

    python scripts/migrate.py            # apply everything pending
    python scripts/migrate.py --status   # show what is applied vs pending
    python scripts/migrate.py --dry-run  # print the plan, change nothing

How it works
------------
Every ``*.sql`` file in ``migrations/`` is applied once, in filename order,
each inside its own transaction. Applied files are recorded in the
``schema_migrations`` table together with a checksum, so an edit to a file that
already ran is reported loudly instead of silently diverging.

To add a schema change: create the next numbered file (``0003_....sql``) and run
the command. That is the whole workflow.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

# Allow `python scripts/migrate.py` from the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psycopg  # noqa: E402

from app.core.config import get_settings  # noqa: E402

MIGRATIONS_DIR = PROJECT_ROOT / "migrations"

_CREATE_TRACKING_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT PRIMARY KEY,
    checksum    TEXT NOT NULL,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def _checksum(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()[:16]


def _discover() -> list[Path]:
    if not MIGRATIONS_DIR.is_dir():
        raise SystemExit(f"No migrations directory at {MIGRATIONS_DIR}")
    return sorted(MIGRATIONS_DIR.glob("*.sql"), key=lambda p: p.name)


def _applied(conn: psycopg.Connection) -> dict[str, str]:
    with conn.cursor() as cur:
        cur.execute(_CREATE_TRACKING_TABLE)
        conn.commit()
        cur.execute("SELECT version, checksum FROM schema_migrations")
        return {row[0]: row[1] for row in cur.fetchall()}


def run(status_only: bool = False, dry_run: bool = False) -> int:
    settings = get_settings()
    files = _discover()

    # psycopg3 speaks the raw Neon DSN (sslmode=require) without translation.
    with psycopg.connect(settings.DATABASE_URL, autocommit=False) as conn:
        applied = _applied(conn)

        pending: list[Path] = []
        for path in files:
            sql = path.read_text(encoding="utf-8")
            digest = _checksum(sql)
            if path.name in applied:
                if applied[path.name] != digest:
                    print(
                        f"  ! {path.name} was modified after it was applied "
                        f"(recorded {applied[path.name]}, now {digest}). "
                        f"Add a new migration instead of editing this one."
                    )
                else:
                    print(f"  = {path.name} (already applied)")
            else:
                pending.append(path)

        if status_only:
            for path in pending:
                print(f"  + {path.name} (pending)")
            print(f"\n{len(applied)} applied, {len(pending)} pending.")
            return 0

        if not pending:
            print("\nDatabase is up to date; nothing to apply.")
            return 0

        for path in pending:
            sql = path.read_text(encoding="utf-8")
            if dry_run:
                print(f"  + {path.name} (would apply, {len(sql)} bytes)")
                continue
            print(f"  + applying {path.name} ...", end=" ", flush=True)
            try:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    cur.execute(
                        "INSERT INTO schema_migrations (version, checksum) VALUES (%s, %s)",
                        (path.name, _checksum(sql)),
                    )
                conn.commit()
            except Exception as exc:
                conn.rollback()
                print("FAILED")
                print(f"\n{path.name} failed and was rolled back:\n  {exc}")
                return 1
            print("ok")

        print(f"\n{len(pending)} migration(s) applied.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply SQL migrations in order.")
    parser.add_argument("--status", action="store_true", help="show state, apply nothing")
    parser.add_argument("--dry-run", action="store_true", help="print the plan only")
    args = parser.parse_args()

    print(f"Migrations directory: {MIGRATIONS_DIR}")
    return run(status_only=args.status, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
