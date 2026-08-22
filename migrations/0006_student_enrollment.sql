-- 0006_student_enrollment.sql
-- Add enrollment fields to students (nullable until post-login enroll step).

ALTER TABLE students
    ADD COLUMN IF NOT EXISTS domain_id UUID REFERENCES domains (id),
    ADD COLUMN IF NOT EXISTS internship_plan_id UUID REFERENCES internship_plans (id),
    ADD COLUMN IF NOT EXISTS chosen_duration_weeks INTEGER,
    ADD COLUMN IF NOT EXISTS college VARCHAR(255),
    ADD COLUMN IF NOT EXISTS year_of_study VARCHAR(64);

CREATE INDEX IF NOT EXISTS students_domain_id_idx ON students (domain_id);
CREATE INDEX IF NOT EXISTS students_internship_plan_id_idx ON students (internship_plan_id);
