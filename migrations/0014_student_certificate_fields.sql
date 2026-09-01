-- 0014_student_certificate_fields.sql
-- Name and internship dates printed on offer letter and certificate.

ALTER TABLE students
    ADD COLUMN IF NOT EXISTS certificate_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS internship_start_date DATE,
    ADD COLUMN IF NOT EXISTS internship_end_date DATE;
