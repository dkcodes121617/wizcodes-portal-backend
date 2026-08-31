-- 0010_domains_slug_and_seed.sql
-- Add slug for API/frontend compatibility and seed the three internship domains.

ALTER TABLE domains
    ADD COLUMN IF NOT EXISTS slug VARCHAR(64);

INSERT INTO domains (name, slug, description, is_active)
VALUES
    ('Web Development', 'web', 'React, APIs, shipped code', TRUE),
    ('AI / ML', 'ai', 'Real datasets, real models', TRUE),
    ('Mobile Development', 'mobile', 'Screens, hooks, shipped apps', TRUE)
ON CONFLICT (name) DO UPDATE
    SET slug = EXCLUDED.slug,
        description = EXCLUDED.description,
        is_active = EXCLUDED.is_active;

ALTER TABLE domains
    ALTER COLUMN slug SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS domains_slug_key ON domains (slug);
