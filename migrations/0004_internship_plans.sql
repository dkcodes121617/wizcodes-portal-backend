-- 0004_internship_plans.sql
-- Internship plans (Basic / Premium). Independent of domain — students pick one
-- of each at enrollment time in a later migration.

CREATE TABLE IF NOT EXISTS internship_plans (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tier                VARCHAR(32) NOT NULL UNIQUE,
    price               INTEGER NOT NULL,
    min_duration_weeks  INTEGER NOT NULL,
    max_duration_weeks  INTEGER NOT NULL,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT internship_plans_duration_range_valid
        CHECK (min_duration_weeks <= max_duration_weeks),
    CONSTRAINT internship_plans_price_positive
        CHECK (price > 0),
    CONSTRAINT internship_plans_duration_positive
        CHECK (min_duration_weeks > 0 AND max_duration_weeks > 0)
);

CREATE INDEX IF NOT EXISTS internship_plans_is_active_idx ON internship_plans (is_active);

DROP TRIGGER IF EXISTS internship_plans_set_updated_at ON internship_plans;
CREATE TRIGGER internship_plans_set_updated_at
    BEFORE UPDATE ON internship_plans
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();
