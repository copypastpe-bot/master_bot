-- Migration 022: Add 5 dark styles, deactivate 3 light styles

-- 1. Deactivate 3 light styles (do NOT delete — existing pages keep working)
UPDATE promo_styles SET is_active = 0 WHERE slug = 'blue';
UPDATE promo_styles SET is_active = 0 WHERE slug = 'premium';
UPDATE promo_styles SET is_active = 0 WHERE slug = 'classic';

-- 2. Add 5 new dark styles

-- category_id uses legacy promo_categories (NOT NULL constraint):
--   1=cleaning, 2=barber, 3=manicure, 4=massage, 5=tutor
INSERT INTO promo_styles (category_id, slug, name, config, sort_order, is_active, suggested_category_id)
VALUES (
    1,
    'midnight_blue',
    'Полночный синий',
    '{"screen_bg":"#0f1923","screen_fg":"#e8edf4","screen_muted":"#8b9bb4","screen_accent":"#4f9cf9","badge_bg":"rgba(15,25,35,.78)","badge_fg":"#4f9cf9","badge_border":"rgba(79,156,249,.35)","card_bg":"#162030","card_border":"#1e2d42","pill_bg":"#1a2840","pill_border":"#2a4060","offer_bg":"#1a2235","offer_border":"#2a3a55","offer_fg":"#4f9cf9","cta_bg":"#4f9cf9","cta_fg":"#0f1923","cta_shadow":"rgba(79,156,249,.20)","is_dark":true}',
    20,
    1,
    (SELECT id FROM master_categories WHERE slug = 'cleaning')
);

INSERT INTO promo_styles (category_id, slug, name, config, sort_order, is_active, suggested_category_id)
VALUES (
    1,
    'deep_forest',
    'Тёмный лес',
    '{"screen_bg":"#0e1a14","screen_fg":"#dce8e0","screen_muted":"#7a9a85","screen_accent":"#34d399","badge_bg":"rgba(14,26,20,.78)","badge_fg":"#34d399","badge_border":"rgba(52,211,153,.35)","card_bg":"#142820","card_border":"#1e3a2c","pill_bg":"#183025","pill_border":"#28503a","offer_bg":"#162218","offer_border":"#253a28","offer_fg":"#34d399","cta_bg":"#34d399","cta_fg":"#0e1a14","cta_shadow":"rgba(52,211,153,.20)","is_dark":true}',
    21,
    1,
    (SELECT id FROM master_categories WHERE slug = 'gardener')
);

INSERT INTO promo_styles (category_id, slug, name, config, sort_order, is_active, suggested_category_id)
VALUES (
    3,
    'charcoal_rose',
    'Графит и роза',
    '{"screen_bg":"#1a1418","screen_fg":"#f0e4ea","screen_muted":"#a08898","screen_accent":"#e88aab","badge_bg":"rgba(26,20,24,.78)","badge_fg":"#e88aab","badge_border":"rgba(232,138,171,.35)","card_bg":"#241c22","card_border":"#35282f","pill_bg":"#2a1e28","pill_border":"#4a3540","offer_bg":"#221a1e","offer_border":"#3a2830","offer_fg":"#e88aab","cta_bg":"#e88aab","cta_fg":"#1a1418","cta_shadow":"rgba(232,138,171,.20)","is_dark":true}',
    22,
    1,
    (SELECT id FROM master_categories WHERE slug = 'beauty')
);

INSERT INTO promo_styles (category_id, slug, name, config, sort_order, is_active, suggested_category_id)
VALUES (
    5,
    'dark_plum',
    'Тёмная слива',
    '{"screen_bg":"#14101e","screen_fg":"#e4dff0","screen_muted":"#8a80a8","screen_accent":"#a78bfa","badge_bg":"rgba(20,16,30,.78)","badge_fg":"#a78bfa","badge_border":"rgba(167,139,250,.35)","card_bg":"#1c1628","card_border":"#2a2040","pill_bg":"#201a30","pill_border":"#382a55","offer_bg":"#1a1425","offer_border":"#2a2040","offer_fg":"#a78bfa","cta_bg":"#a78bfa","cta_fg":"#14101e","cta_shadow":"rgba(167,139,250,.20)","is_dark":true}',
    23,
    1,
    (SELECT id FROM master_categories WHERE slug = 'psychologist')
);

INSERT INTO promo_styles (category_id, slug, name, config, sort_order, is_active, suggested_category_id)
VALUES (
    2,
    'warm_noir',
    'Тёплый нуар',
    '{"screen_bg":"#171310","screen_fg":"#f0ebe4","screen_muted":"#a09080","screen_accent":"#e8a840","badge_bg":"rgba(23,19,16,.78)","badge_fg":"#e8a840","badge_border":"rgba(232,168,64,.35)","card_bg":"#221c18","card_border":"#342a22","pill_bg":"#282018","pill_border":"#4a3820","offer_bg":"#1e1a14","offer_border":"#382e20","offer_fg":"#e8a840","cta_bg":"#e8a840","cta_fg":"#171310","cta_shadow":"rgba(232,168,64,.20)","is_dark":true}',
    24,
    1,
    (SELECT id FROM master_categories WHERE slug = 'handyman')
);

-- 3. Update category_default_styles: replace deactivated styles with active ones

-- blue (tutor default) → academic
UPDATE category_default_styles
SET style_id = (SELECT id FROM promo_styles WHERE slug = 'academic' AND is_active = 1)
WHERE style_id = (SELECT id FROM promo_styles WHERE slug = 'blue');

-- premium (cleaning default) → fresh_green
UPDATE category_default_styles
SET style_id = (SELECT id FROM promo_styles WHERE slug = 'fresh_green' AND is_active = 1)
WHERE style_id = (SELECT id FROM promo_styles WHERE slug = 'premium');

-- classic (barber default) → dark
UPDATE category_default_styles
SET style_id = (SELECT id FROM promo_styles WHERE slug = 'dark' AND is_active = 1)
WHERE style_id = (SELECT id FROM promo_styles WHERE slug = 'classic');

-- Update defaults for categories that now have a dedicated dark style
UPDATE category_default_styles
SET style_id = (SELECT id FROM promo_styles WHERE slug = 'deep_forest')
WHERE category_id = (SELECT id FROM master_categories WHERE slug = 'gardener');

UPDATE category_default_styles
SET style_id = (SELECT id FROM promo_styles WHERE slug = 'charcoal_rose')
WHERE category_id = (SELECT id FROM master_categories WHERE slug = 'grooming');

UPDATE category_default_styles
SET style_id = (SELECT id FROM promo_styles WHERE slug = 'dark_plum')
WHERE category_id = (SELECT id FROM master_categories WHERE slug = 'psychologist');

UPDATE category_default_styles
SET style_id = (SELECT id FROM promo_styles WHERE slug = 'warm_noir')
WHERE category_id = (SELECT id FROM master_categories WHERE slug = 'handyman');

UPDATE category_default_styles
SET style_id = (SELECT id FROM promo_styles WHERE slug = 'warm_noir')
WHERE category_id = (SELECT id FROM master_categories WHERE slug = 'appliance_repair');
