-- 0002_students.sql
-- Student accounts for signup/login. Enrollment fields come in a later migration.

CREATE TABLE IF NOT EXISTS students (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          VARCHAR(255) NOT NULL,
    email         VARCHAR(320) UNIQUE,
    phone         VARCHAR(32) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT students_email_or_phone_required
        CHECK (email IS NOT NULL OR phone IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS students_email_idx ON students (email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS students_phone_idx ON students (phone) WHERE phone IS NOT NULL;

DROP TRIGGER IF EXISTS students_set_updated_at ON students;
CREATE TRIGGER students_set_updated_at
    BEFORE UPDATE ON students
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();
