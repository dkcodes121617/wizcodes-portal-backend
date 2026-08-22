-- 0007_student_payment.sql
-- Payment screenshot path and manual access-review status on students.

ALTER TABLE students
    ADD COLUMN IF NOT EXISTS payment_screenshot_url VARCHAR(512),
    ADD COLUMN IF NOT EXISTS access_status VARCHAR(32) NOT NULL DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS access_granted_by VARCHAR(64);

ALTER TABLE students
    DROP CONSTRAINT IF EXISTS students_access_status_valid;

ALTER TABLE students
    ADD CONSTRAINT students_access_status_valid
        CHECK (access_status IN ('pending', 'granted'));
