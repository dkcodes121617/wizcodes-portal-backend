-- 0009_admins.sql
-- Admin accounts for portal management (separate from students).

CREATE TABLE IF NOT EXISTS admins (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          VARCHAR(255) NOT NULL,
    email         VARCHAR(320) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(32) NOT NULL DEFAULT 'admin',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT admins_role_valid
        CHECK (role IN ('admin', 'super_admin'))
);

CREATE INDEX IF NOT EXISTS admins_email_idx ON admins (email);

DROP TRIGGER IF EXISTS admins_set_updated_at ON admins;
CREATE TRIGGER admins_set_updated_at
    BEFORE UPDATE ON admins
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();
