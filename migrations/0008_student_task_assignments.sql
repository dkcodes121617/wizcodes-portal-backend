-- 0008_student_task_assignments.sql
-- Per-student task assignments (Basic auto-assigned, Premium manual in A10).

CREATE TABLE IF NOT EXISTS student_task_assignments (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id       UUID NOT NULL REFERENCES students (id),
    task_id          UUID NOT NULL REFERENCES tasks (id),
    assigned_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_by      VARCHAR(64) NOT NULL,
    status           VARCHAR(32) NOT NULL DEFAULT 'assigned',
    submission_link  VARCHAR(2048),
    submitted_at     TIMESTAMPTZ,
    admin_feedback   TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT student_task_assignments_status_valid
        CHECK (status IN ('assigned', 'in_progress', 'submitted', 'completed')),
    CONSTRAINT student_task_assignments_student_task_unique
        UNIQUE (student_id, task_id)
);

CREATE INDEX IF NOT EXISTS student_task_assignments_student_id_idx
    ON student_task_assignments (student_id);
CREATE INDEX IF NOT EXISTS student_task_assignments_task_id_idx
    ON student_task_assignments (task_id);
CREATE INDEX IF NOT EXISTS student_task_assignments_status_idx
    ON student_task_assignments (status);

DROP TRIGGER IF EXISTS student_task_assignments_set_updated_at ON student_task_assignments;
CREATE TRIGGER student_task_assignments_set_updated_at
    BEFORE UPDATE ON student_task_assignments
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();
