"""Delete all application data while keeping the schema and migration history.

    python scripts/clear_database.py
    python scripts/clear_database.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psycopg  # noqa: E402
from psycopg import sql  # noqa: E402

from app.core.config import get_settings  # noqa: E402

KEEP_TABLES = frozenset({"schema_migrations"})


def list_tables(conn: psycopg.Connection) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
            """
        )
        return [row[0] for row in cur.fetchall()]


def count_rows(conn: psycopg.Connection, table: str) -> int:
    with conn.cursor() as cur:
        cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
        return cur.fetchone()[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Clear all data from the database.")
    parser.add_argument("--dry-run", action="store_true", help="show plan only")
    args = parser.parse_args()

    settings = get_settings()
    with psycopg.connect(settings.DATABASE_URL) as conn:
        tables = list_tables(conn)
        to_clear = [table for table in tables if table not in KEEP_TABLES]

        if not to_clear:
            print("No tables to clear.")
            return 0

        print("Tables to clear:")
        for table in to_clear:
            try:
                count = count_rows(conn, table)
            except Exception:
                count = "?"
            print(f"  - {table}: {count} row(s)")

        if args.dry_run:
            print("\nDry run — no changes made.")
            return 0

        truncate_sql = sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(
            sql.SQL(", ").join(sql.Identifier(table) for table in to_clear)
        )

        with conn.cursor() as cur:
            cur.execute(truncate_sql)
        conn.commit()

        print(f"\nCleared {len(to_clear)} table(s). schema_migrations was kept.")
        print(
            "Restart the backend to recreate the admin from "
            "ADMIN_EMAIL / ADMIN_PASSWORD in .env."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
