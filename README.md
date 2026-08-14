# WizCodes Portal — Backend

FastAPI + Neon Postgres 18, running on Python 3.11.

- **Deploys to:** Render (see [DEPLOYMENT.md](DEPLOYMENT.md))
- **Frontend:** <https://github.com/dkcodes121617/wizcodes-portal-frontend>

---

## Quick start

```bash
# 1. Activate the virtual environment
venv\Scripts\activate           # Windows
source venv/bin/activate        # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create your .env  (only DATABASE_URL is required)
copy .env.example .env          # Windows
cp .env.example .env            # macOS/Linux

# 4. Apply the database schema
python scripts/migrate.py

# 5. Run it
python main.py
```

The server starts on <http://localhost:8000> and auto-reloads on save.

| URL                                             | What it is                    |
| ----------------------------------------------- | ----------------------------- |
| <http://localhost:8000/docs>                     | Interactive API documentation |
| <http://localhost:8000/health>                   | Liveness check                |
| <http://localhost:8000/api/v1/health/ready>      | Checks the database connection |

---

## You only configure one thing

`DATABASE_URL`. Everything else has a working default.

The app **detects where it is running**:

|                 | Local machine            | Render (production)                             |
| --------------- | ------------------------ | ----------------------------------------------- |
| `ENVIRONMENT`   | `development`            | `production` (auto)                             |
| `DEBUG`         | on                       | off                                             |
| Auto-reload     | on                       | off                                             |
| Keep-alive ping | off                      | on                                              |
| `SECRET_KEY`    | auto-generated           | required, set on Render                         |
| `FRONTEND_URL`  | `http://localhost:3000`  | `https://wizcodes-portal-frontend.vercel.app`   |
| `PUBLIC_BASE_URL` | *(unused)*             | `RENDER_EXTERNAL_URL`, else the deployed URL    |

You do not flip any of these by hand. Render injects `RENDER=true` into every
service, and the app reads that. If you *want* to override something, uncomment
the matching line in `.env` — the detection only supplies defaults.

Production additionally **refuses to start** on an unsafe config (`DEBUG=true`,
no `SECRET_KEY`), so a mistake surfaces at deploy time rather than silently.

---

## Commands

| Command                            | What it does                              |
| ---------------------------------- | ----------------------------------------- |
| `python main.py`                   | Start the server                           |
| `python scripts/migrate.py`        | Apply pending SQL migrations               |
| `python scripts/migrate.py --status` | Show applied vs pending                  |
| `python scripts/migrate.py --dry-run` | Show the plan, change nothing           |
| `pytest`                           | Run the tests                              |
| `ruff check .`                     | Lint                                       |
| `ruff format .`                    | Format                                     |

---

## Database changes

**No Alembic.** Schema changes are plain `.sql` files, applied in filename order.

To add a table:

1. Create `migrations/0002_whatever.sql` (next number, descriptive name).
2. Write normal SQL. Prefer `IF NOT EXISTS` so re-running is harmless.
3. Run `python scripts/migrate.py`.

Each file runs in its own transaction — it either fully applies or fully rolls
back. Applied files are recorded in the `schema_migrations` table with a
checksum, so editing one that already ran is reported instead of silently
diverging. **Never edit an applied migration; add a new one.**

---

## Project structure

```
wizcodes-portal-backend/
├── main.py                  # entrypoint — `python main.py`
├── app/
│   ├── main.py              # FastAPI app factory, middleware, error handlers
│   ├── core/
│   │   ├── config.py        # all settings + environment auto-detection
│   │   ├── logging.py       # single log format, stdout (Render reads this)
│   │   ├── middleware.py    # request IDs, timing, security headers
│   │   ├── security.py      # password hashing + JWT helpers
│   │   └── keepalive.py     # anti-idle self-ping for Render's free tier
│   ├── db/
│   │   ├── base.py          # SQLAlchemy declarative base + timestamp mixin
│   │   └── session.py       # async engine and per-request session
│   ├── models/              # ORM models  (add yours here)
│   ├── schemas/             # Pydantic request/response shapes
│   └── api/v1/
│       ├── router.py        # aggregates route modules
│       └── routes/          # one file per resource  (add yours here)
├── migrations/              # plain .sql files, applied in order
├── scripts/migrate.py       # the migration runner
└── tests/
```

### Adding an endpoint

1. Model in `app/models/`, and a migration in `migrations/` to create its table.
2. Request/response schemas in `app/schemas/`.
3. Routes in `app/api/v1/routes/yourthing.py`.
4. Register it in `app/api/v1/router.py`.

---

## Security notes

- Secrets come from environment variables only; `.env` is gitignored.
- `SECRET_KEY` is mandatory in production and refuses to fall back to a random
  per-restart value.
- Passwords hash with PBKDF2-HMAC-SHA256 (240k rounds) and verify in constant time.
- Security headers on every response; HSTS added on HTTPS.
- Unhandled exceptions return a generic message plus a request id — internals are
  never sent to the client. The detail goes to the logs.
- Every response carries `X-Request-ID`; use it to find the matching log line.
- **CORS is `*` by explicit request.** Because of that, credentialed requests are
  disabled (browsers reject `*` + credentials). Authenticate with a bearer token
  in the `Authorization` header, not cookies.
