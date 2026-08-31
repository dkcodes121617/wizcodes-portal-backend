-- 0013_notifications.sql
-- In-app notifications for students (sent by admins).

CREATE TABLE IF NOT EXISTS notifications (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id        UUID NOT NULL REFERENCES students (id) ON DELETE CASCADE,
    title             VARCHAR(255) NOT NULL,
    body              TEXT NOT NULL,
    read_at           TIMESTAMPTZ,
    sent_by_admin_id  UUID REFERENCES admins (id) ON DELETE SET NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS notifications_student_created_idx
    ON notifications (student_id, created_at DESC);

CREATE INDEX IF NOT EXISTS notifications_student_unread_idx
    ON notifications (student_id)
    WHERE read_at IS NULL;

DROP TRIGGER IF EXISTS notifications_set_updated_at ON notifications;
CREATE TRIGGER notifications_set_updated_at
    BEFORE UPDATE ON notifications
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();
