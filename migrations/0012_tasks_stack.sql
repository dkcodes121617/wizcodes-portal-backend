-- Replace github_link with stack (title + description + stack for students).

ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS stack VARCHAR(500) NOT NULL DEFAULT 'Not specified';

UPDATE tasks
SET stack = 'Not specified'
WHERE stack IS NULL OR btrim(stack) = '';

ALTER TABLE tasks
    DROP COLUMN IF EXISTS github_link;
