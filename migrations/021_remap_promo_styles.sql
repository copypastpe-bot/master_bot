-- Migration 021: Remap promo styles and advantages to master_categories.
-- Adds suggested_category_id (nullable) to promo_styles and promo_advantages.
-- Creates category_default_styles lookup table.
-- Does NOT drop promo_categories or the legacy category_id FK.

-- 1. New columns (nullable — existing rows get NULL, filled below).
ALTER TABLE promo_styles     ADD COLUMN suggested_category_id INTEGER REFERENCES master_categories(id);
ALTER TABLE promo_advantages ADD COLUMN suggested_category_id INTEGER REFERENCES master_categories(id);

-- 2. Map promo_styles: promo_categories.slug → master_categories.slug.
UPDATE promo_styles
SET suggested_category_id = (SELECT id FROM master_categories WHERE slug = 'cleaning')
WHERE category_id = (SELECT id FROM promo_categories WHERE slug = 'cleaning');

UPDATE promo_styles
SET suggested_category_id = (SELECT id FROM master_categories WHERE slug = 'barber')
WHERE category_id = (SELECT id FROM promo_categories WHERE slug = 'barber');

UPDATE promo_styles
SET suggested_category_id = (SELECT id FROM master_categories WHERE slug = 'beauty')
WHERE category_id = (SELECT id FROM promo_categories WHERE slug = 'manicure');

UPDATE promo_styles
SET suggested_category_id = (SELECT id FROM master_categories WHERE slug = 'massage')
WHERE category_id = (SELECT id FROM promo_categories WHERE slug = 'massage');

UPDATE promo_styles
SET suggested_category_id = (SELECT id FROM master_categories WHERE slug = 'tutor')
WHERE category_id = (SELECT id FROM promo_categories WHERE slug = 'tutor');

-- 3. Map promo_advantages: same slug mapping.
UPDATE promo_advantages
SET suggested_category_id = (SELECT id FROM master_categories WHERE slug = 'cleaning')
WHERE category_id = (SELECT id FROM promo_categories WHERE slug = 'cleaning');

UPDATE promo_advantages
SET suggested_category_id = (SELECT id FROM master_categories WHERE slug = 'barber')
WHERE category_id = (SELECT id FROM promo_categories WHERE slug = 'barber');

UPDATE promo_advantages
SET suggested_category_id = (SELECT id FROM master_categories WHERE slug = 'beauty')
WHERE category_id = (SELECT id FROM promo_categories WHERE slug = 'manicure');

UPDATE promo_advantages
SET suggested_category_id = (SELECT id FROM master_categories WHERE slug = 'massage')
WHERE category_id = (SELECT id FROM promo_categories WHERE slug = 'massage');

UPDATE promo_advantages
SET suggested_category_id = (SELECT id FROM master_categories WHERE slug = 'tutor')
WHERE category_id = (SELECT id FROM promo_categories WHERE slug = 'tutor');

-- 4. Default style lookup table (one default per master_category).
CREATE TABLE IF NOT EXISTS category_default_styles (
    category_id INTEGER NOT NULL REFERENCES master_categories(id),
    style_id    INTEGER NOT NULL REFERENCES promo_styles(id),
    UNIQUE(category_id)
);

-- 4a. Categories that have their own suggested styles → use the first one (lowest sort_order).
INSERT OR IGNORE INTO category_default_styles (category_id, style_id)
SELECT mc.id,
       (SELECT ps.id FROM promo_styles ps
        WHERE ps.suggested_category_id = mc.id AND ps.is_active = 1
        ORDER BY ps.sort_order ASC, ps.id ASC
        LIMIT 1)
FROM master_categories mc
WHERE EXISTS (
    SELECT 1 FROM promo_styles ps
    WHERE ps.suggested_category_id = mc.id AND ps.is_active = 1
);

-- 4b. New master_categories without own styles → nearest existing style.
-- Note: slugs reflect current state after migration 018 (018_update_promo_styles.sql):
--   pink (was soft_pink), nude (was lavender), classic (was urban),
--   warm_beige (was calm_blue), blue (was bright/academic).
INSERT OR IGNORE INTO category_default_styles (category_id, style_id) VALUES
    ((SELECT id FROM master_categories WHERE slug = 'dry_cleaning'),     (SELECT id FROM promo_styles WHERE slug = 'fresh_green')),
    ((SELECT id FROM master_categories WHERE slug = 'grooming'),         (SELECT id FROM promo_styles WHERE slug = 'pink')),
    ((SELECT id FROM master_categories WHERE slug = 'appliance_repair'), (SELECT id FROM promo_styles WHERE slug = 'classic')),
    ((SELECT id FROM master_categories WHERE slug = 'handyman'),         (SELECT id FROM promo_styles WHERE slug = 'classic')),
    ((SELECT id FROM master_categories WHERE slug = 'photographer'),     (SELECT id FROM promo_styles WHERE slug = 'nude')),
    ((SELECT id FROM master_categories WHERE slug = 'psychologist'),     (SELECT id FROM promo_styles WHERE slug = 'warm_beige')),
    ((SELECT id FROM master_categories WHERE slug = 'gardener'),         (SELECT id FROM promo_styles WHERE slug = 'fresh_green')),
    ((SELECT id FROM master_categories WHERE slug = 'other'),            (SELECT id FROM promo_styles WHERE slug = 'blue'));
