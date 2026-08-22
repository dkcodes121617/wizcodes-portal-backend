"""Bootstrap the first super_admin account (run once locally).

    python scripts/create_first_admin.py --name "Wizard" --email admin@wizcodes.com

Prompts for a password if --password is not supplied.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psycopg  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the first super_admin account")
    parser.add_argument("--name", required=True, help="Admin display name")
    parser.add_argument("--email", required=True, help="Admin login email")
    parser.add_argument("--password", help="Password (omit to be prompted securely)")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Password: ")
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters.")

    email = args.email.strip().lower()
    settings = get_settings()

    with psycopg.connect(settings.DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM admins")
            if cur.fetchone()[0] > 0:
                raise SystemExit("Admins already exist — use POST /api/v1/auth/admin/create instead.")

            cur.execute(
                """
                INSERT INTO admins (name, email, password_hash, role)
                VALUES (%s, %s, %s, 'super_admin')
                RETURNING id::text
                """,
                (args.name.strip(), email, hash_password(password)),
            )
            admin_id = cur.fetchone()[0]
        conn.commit()

    print(f"Created super_admin {email} (id={admin_id})")


if __name__ == "__main__":
    main()
