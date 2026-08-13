-- 0001_init.sql
-- Baseline extensions and helpers. Applied once, in filename order, by
-- `python scripts/migrate.py`.
--
-- Every migration runs inside a single transaction. Write statements that are
-- safe to re-run (IF NOT EXISTS) so a partially-reviewed change is never a trap.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Keeps updated_at honest without relying on the application layer.
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
