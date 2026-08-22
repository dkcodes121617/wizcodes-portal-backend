-- 0005_tasks.sql
-- Shared task bank for Basic and Premium plans, keyed by domain + plan.

CREATE TABLE IF NOT EXISTS tasks (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id           UUID NOT NULL REFERENCES domains (id),
    internship_plan_id  UUID NOT NULL REFERENCES internship_plans (id),
    title               VARCHAR(255) NOT NULL,
    description         TEXT NOT NULL,
    github_link         VARCHAR(2048) NOT NULL,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS tasks_domain_id_idx ON tasks (domain_id);
CREATE INDEX IF NOT EXISTS tasks_internship_plan_id_idx ON tasks (internship_plan_id);
CREATE INDEX IF NOT EXISTS tasks_is_active_idx ON tasks (is_active);
CREATE INDEX IF NOT EXISTS tasks_domain_plan_idx ON tasks (domain_id, internship_plan_id);

DROP TRIGGER IF EXISTS tasks_set_updated_at ON tasks;
CREATE TRIGGER tasks_set_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();
