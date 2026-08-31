-- 0011_internship_plans_seed.sql
-- Seed the Basic and Premium plans shown on the marketing site.

INSERT INTO internship_plans (tier, price, min_duration_weeks, max_duration_weeks, is_active)
VALUES
    ('basic_299', 299, 2, 6, TRUE),
    ('premium_999', 999, 2, 12, TRUE)
ON CONFLICT (tier) DO UPDATE
    SET price = EXCLUDED.price,
        min_duration_weeks = EXCLUDED.min_duration_weeks,
        max_duration_weeks = EXCLUDED.max_duration_weeks,
        is_active = EXCLUDED.is_active;
