# Deploying the backend to Render

Deploy the **backend first** — the frontend needs its URL.

Everything below is a one-time setup. After it, every push to `main` redeploys
automatically.

---

## 0. Before you start

You need:

- The GitHub repo pushed to `main` (already done).
- Your Neon connection string.
- A Render account: <https://dashboard.render.com>

---

## 1. Create the Web Service

1. Go to <https://dashboard.render.com> → **New +** → **Web Service**.
2. **Connect the repository** `dkcodes121617/wizcodes-portal-backend`.
   (First time only: click *Configure account* and grant Render access to the repo.)
3. Fill in the form exactly:

   | Field              | Value                                             |
   | ------------------ | ------------------------------------------------- |
   | **Name**           | `wizcodes-portal-backend`                          |
   | **Language**       | `Python 3`                                         |
   | **Branch**         | `main`                                             |
   | **Region**         | `Ohio (US East)` — same region as the Neon project |
   | **Root Directory** | *(leave blank)*                                    |
   | **Build Command**  | `pip install --upgrade pip && pip install -r requirements.txt` |
   | **Start Command**  | `python main.py`                                   |
   | **Instance Type**  | `Free`                                             |

> Alternative: **New +** → **Blueprint** and point it at this repo. Render reads
> `render.yaml` and fills all of the above in for you. You still have to supply
> the two secret values in step 2.

---

## 2. Environment variables

Scroll to **Environment Variables** and add these three:

| Key              | Value                                                          |
| ---------------- | -------------------------------------------------------------- |
| `DATABASE_URL`   | your full Neon connection string, including `?sslmode=require`  |
| `SECRET_KEY`     | click **Generate** (Render creates a strong random value)       |
| `PYTHON_VERSION` | `3.11.9`                                                        |

That is all. **Do not set** `PORT`, `ENVIRONMENT`, `DEBUG`, or `RELOAD` —
Render injects `PORT`, and the app detects that it is running on Render and
switches itself to production mode.

`FRONTEND_URL` also needs no setting: on Render it resolves to
`https://wizcodes-portal-frontend.vercel.app` automatically. Set it only if you
move the frontend to a custom domain.

---

## 3. Health check

Under **Health Check Path**, enter:

```
/health
```

Render uses this to decide whether a deploy succeeded.

---

## 4. Deploy

Click **Create Web Service**. The first build takes 2–4 minutes.

When it finishes you get a URL like:

```
https://wizcodes-portal-backend.onrender.com
```

**Verify it before moving on:**

| URL                                | Expected                                          |
| ---------------------------------- | ------------------------------------------------- |
| `/health`                          | `{"status":"ok"}`                                  |
| `/api/v1/health/ready`             | `{"status":"ok","database":"up",...}` ← proves Neon works |
| `/docs`                            | the interactive API documentation                  |

If `/api/v1/health/ready` says `"database":"down"`, the `DATABASE_URL` is wrong —
check it in the Render dashboard. The response includes the reason.

---

## 5. After the frontend is live

Nothing to do — `FRONTEND_URL` already resolves to
`https://wizcodes-portal-frontend.vercel.app` on Render, and CORS is `*` so the
frontend works regardless.

Only if you move to a custom domain, add:

| Key            | Value                          |
| -------------- | ------------------------------ |
| `FRONTEND_URL` | `https://portal.wizcodes.com`  |

---

## 6. Stop the free tier from sleeping

Render's free tier sleeps after ~15 minutes with no traffic, and waking up takes
about 50 seconds. Two mechanisms handle this, and they cover different cases:

**a) Built in, already running.** The app pings its own `/keepalive` endpoint
every 14 minutes while it is awake. Nothing to configure — it activates
automatically on Render and stays off locally. Confirm it in the Render logs:

```
Keep-alive enabled: pinging https://....onrender.com/keepalive every 840s
```

**b) GitHub Actions cron — the backup that can also *wake* a sleeping service.**
A sleeping app cannot ping itself, so this one matters after any long idle gap.

1. GitHub repo → **Settings** → **Secrets and variables** → **Actions**
2. Open the **Variables** tab → **New repository variable**
3. Name: `BACKEND_URL`, Value: `https://wizcodes-portal-backend.onrender.com`

The workflow in `.github/workflows/keepalive.yml` runs every 14 minutes.

> GitHub disables scheduled workflows in a repo with no commits for 60 days.
> If pings stop, re-enable the workflow from the **Actions** tab.

---

## 7. Database migrations

There is no Alembic. Schema changes are plain `.sql` files applied in order.

To add a change:

1. Create the next numbered file, e.g. `migrations/0002_projects.sql`.
2. Run it locally first: `python scripts/migrate.py`
3. Commit and push.

To apply migrations against the production database, run the script locally with
the production `DATABASE_URL`:

```bash
# macOS/Linux
DATABASE_URL="<neon-connection-string>" python scripts/migrate.py

# Windows PowerShell
$env:DATABASE_URL="<neon-connection-string>"; python scripts/migrate.py
```

Useful flags:

```bash
python scripts/migrate.py --status    # what is applied vs pending
python scripts/migrate.py --dry-run   # show the plan, change nothing
```

Each file runs inside its own transaction and is recorded with a checksum, so a
migration can never half-apply, and editing one that already ran is reported
instead of silently ignored.

---

## Troubleshooting

| Symptom                              | Cause and fix                                                                 |
| ------------------------------------ | ----------------------------------------------------------------------------- |
| Deploy fails: `SECRET_KEY must be set explicitly` | Add `SECRET_KEY` in the Render dashboard (use **Generate**).       |
| Deploy fails: `DATABASE_URL must be set` | Add `DATABASE_URL` in the Render dashboard.                               |
| `"database":"down"` on readiness     | Wrong connection string, or the `?sslmode=require` suffix was dropped.         |
| First request after idle takes ~50s  | Free-tier cold start. Set up the keep-alive in step 6.                        |
| Deploy fails: `DEBUG must be false in production` | Remove any `DEBUG` variable you added — it is derived automatically. |
| Port binding errors                  | Do not set `PORT` yourself; Render injects it.                                |
