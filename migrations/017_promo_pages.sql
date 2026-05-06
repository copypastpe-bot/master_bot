-- Migration 017: promo page constructor database schema and MVP seed data

CREATE TABLE IF NOT EXISTS promo_categories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    icon            TEXT,
    sort_order      INTEGER DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS promo_styles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id     INTEGER NOT NULL REFERENCES promo_categories(id),
    slug            TEXT NOT NULL,
    name            TEXT NOT NULL,
    config          TEXT NOT NULL,
    sort_order      INTEGER DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category_id, slug)
);

CREATE TABLE IF NOT EXISTS promo_advantages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id     INTEGER NOT NULL REFERENCES promo_categories(id),
    text            TEXT NOT NULL,
    icon            TEXT,
    sort_order      INTEGER DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,
    UNIQUE(category_id, text)
);

CREATE TABLE IF NOT EXISTS promo_pages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id       INTEGER NOT NULL REFERENCES masters(id),
    slug            TEXT UNIQUE NOT NULL,
    category_id     INTEGER NOT NULL REFERENCES promo_categories(id),
    style_id        INTEGER NOT NULL REFERENCES promo_styles(id),
    display_name    TEXT NOT NULL,
    specialization  TEXT NOT NULL,
    tagline         TEXT NOT NULL,
    badge_text      TEXT,
    service_name    TEXT NOT NULL,
    service_price   TEXT NOT NULL,
    promo_text      TEXT,
    promo_enabled   BOOLEAN DEFAULT FALSE,
    advantages      TEXT NOT NULL,
    sub_button_text TEXT DEFAULT 'Бонусы и уведомления в Telegram',
    photo_path      TEXT,
    photo_url       TEXT,
    qr_path         TEXT,
    qr_url          TEXT,
    is_published    BOOLEAN DEFAULT FALSE,
    views_count     INTEGER DEFAULT 0,
    clicks_count    INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(master_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_promo_pages_slug ON promo_pages(slug);
CREATE INDEX IF NOT EXISTS idx_promo_pages_master ON promo_pages(master_id);
CREATE INDEX IF NOT EXISTS idx_promo_styles_category ON promo_styles(category_id);
CREATE INDEX IF NOT EXISTS idx_promo_advantages_category ON promo_advantages(category_id);

INSERT OR IGNORE INTO promo_categories (slug, name, icon, sort_order) VALUES
    ('cleaning', 'Клининг', '🧹', 10),
    ('barber', 'Парикмахер / барбер', '💈', 20),
    ('manicure', 'Маникюр и бьюти-услуги', '💅', 30),
    ('massage', 'Массаж', '🤲', 40),
    ('tutor', 'Репетитор', '📚', 50);

INSERT OR IGNORE INTO promo_styles (category_id, slug, name, config, sort_order)
SELECT id, 'fresh_green', 'Свежий зелёный', '{"primary_color":"#2E7D32","secondary_color":"#E8F5E9","accent_color":"#1B5E20","text_color":"#212121","text_color_light":"#FFFFFF","bg_color":"#FFFFFF","badge_bg":"#2E7D32","badge_text":"#FFFFFF","button_bg":"#2E7D32","button_text":"#FFFFFF","card_bg":"#F1F8E9","gradient":"linear-gradient(135deg, #2E7D32 0%, #4CAF50 100%)","icon_set":"cleaning_fresh"}', 10
FROM promo_categories WHERE slug = 'cleaning';
INSERT OR IGNORE INTO promo_styles (category_id, slug, name, config, sort_order)
SELECT id, 'minimalism', 'Минимализм', '{"primary_color":"#37474F","secondary_color":"#ECEFF1","accent_color":"#263238","text_color":"#212121","text_color_light":"#FFFFFF","bg_color":"#FFFFFF","badge_bg":"#37474F","badge_text":"#FFFFFF","button_bg":"#37474F","button_text":"#FFFFFF","card_bg":"#ECEFF1","gradient":"linear-gradient(135deg, #37474F 0%, #607D8B 100%)","icon_set":"cleaning_minimalism"}', 20
FROM promo_categories WHERE slug = 'cleaning';
INSERT OR IGNORE INTO promo_styles (category_id, slug, name, config, sort_order)
SELECT id, 'premium', 'Премиум', '{"primary_color":"#1A237E","secondary_color":"#E8EAF6","accent_color":"#0D47A1","text_color":"#212121","text_color_light":"#FFFFFF","bg_color":"#FFFFFF","badge_bg":"#1A237E","badge_text":"#FFFFFF","button_bg":"#1A237E","button_text":"#FFFFFF","card_bg":"#E8EAF6","gradient":"linear-gradient(135deg, #1A237E 0%, #3949AB 100%)","icon_set":"cleaning_premium"}', 30
FROM promo_categories WHERE slug = 'cleaning';

INSERT OR IGNORE INTO promo_styles (category_id, slug, name, config, sort_order)
SELECT id, 'dark', 'Тёмный', '{"primary_color":"#212121","secondary_color":"#424242","accent_color":"#FF6F00","text_color":"#212121","text_color_light":"#FFFFFF","bg_color":"#FFFFFF","badge_bg":"#212121","badge_text":"#FFFFFF","button_bg":"#212121","button_text":"#FFFFFF","card_bg":"#F5F5F5","gradient":"linear-gradient(135deg, #212121 0%, #424242 100%)","icon_set":"barber_dark"}', 10
FROM promo_categories WHERE slug = 'barber';
INSERT OR IGNORE INTO promo_styles (category_id, slug, name, config, sort_order)
SELECT id, 'classic', 'Классический', '{"primary_color":"#3E2723","secondary_color":"#EFEBE9","accent_color":"#5D4037","text_color":"#212121","text_color_light":"#FFFFFF","bg_color":"#FFFFFF","badge_bg":"#3E2723","badge_text":"#FFFFFF","button_bg":"#3E2723","button_text":"#FFFFFF","card_bg":"#EFEBE9","gradient":"linear-gradient(135deg, #3E2723 0%, #6D4C41 100%)","icon_set":"barber_classic"}', 20
FROM promo_categories WHERE slug = 'barber';
INSERT OR IGNORE INTO promo_styles (category_id, slug, name, config, sort_order)
SELECT id, 'modern', 'Современный', '{"primary_color":"#1565C0","secondary_color":"#E3F2FD","accent_color":"#0D47A1","text_color":"#212121","text_color_light":"#FFFFFF","bg_color":"#FFFFFF","badge_bg":"#1565C0","badge_text":"#FFFFFF","button_bg":"#1565C0","button_text":"#FFFFFF","card_bg":"#E3F2FD","gradient":"linear-gradient(135deg, #1565C0 0%, #42A5F5 100%)","icon_set":"barber_modern"}', 30
FROM promo_categories WHERE slug = 'barber';

INSERT OR IGNORE INTO promo_styles (category_id, slug, name, config, sort_order)
SELECT id, 'pink', 'Розовый', '{"primary_color":"#C2185B","secondary_color":"#FCE4EC","accent_color":"#880E4F","text_color":"#212121","text_color_light":"#FFFFFF","bg_color":"#FFFFFF","badge_bg":"#C2185B","badge_text":"#FFFFFF","button_bg":"#C2185B","button_text":"#FFFFFF","card_bg":"#FCE4EC","gradient":"linear-gradient(135deg, #C2185B 0%, #EC407A 100%)","icon_set":"beauty_pink"}', 10
FROM promo_categories WHERE slug = 'manicure';
INSERT OR IGNORE INTO promo_styles (category_id, slug, name, config, sort_order)
SELECT id, 'nude', 'Нюдовый', '{"primary_color":"#8D6E63","secondary_color":"#EFEBE9","accent_color":"#5D4037","text_color":"#212121","text_color_light":"#FFFFFF","bg_color":"#FFFFFF","badge_bg":"#8D6E63","badge_text":"#FFFFFF","button_bg":"#8D6E63","button_text":"#FFFFFF","card_bg":"#EFEBE9","gradient":"linear-gradient(135deg, #8D6E63 0%, #BCAAA4 100%)","icon_set":"beauty_nude"}', 20
FROM promo_categories WHERE slug = 'manicure';
INSERT OR IGNORE INTO promo_styles (category_id, slug, name, config, sort_order)
SELECT id, 'elegant', 'Элегантный', '{"primary_color":"#4A148C","secondary_color":"#F3E5F5","accent_color":"#311B92","text_color":"#212121","text_color_light":"#FFFFFF","bg_color":"#FFFFFF","badge_bg":"#4A148C","badge_text":"#FFFFFF","button_bg":"#4A148C","button_text":"#FFFFFF","card_bg":"#F3E5F5","gradient":"linear-gradient(135deg, #4A148C 0%, #7B1FA2 100%)","icon_set":"beauty_elegant"}', 30
FROM promo_categories WHERE slug = 'manicure';

INSERT OR IGNORE INTO promo_styles (category_id, slug, name, config, sort_order)
SELECT id, 'warm_beige', 'Тёплый беж', '{"primary_color":"#795548","secondary_color":"#EFEBE9","accent_color":"#4E342E","text_color":"#212121","text_color_light":"#FFFFFF","bg_color":"#FFFFFF","badge_bg":"#795548","badge_text":"#FFFFFF","button_bg":"#795548","button_text":"#FFFFFF","card_bg":"#EFEBE9","gradient":"linear-gradient(135deg, #795548 0%, #A1887F 100%)","icon_set":"massage_warm"}', 10
FROM promo_categories WHERE slug = 'massage';
INSERT OR IGNORE INTO promo_styles (category_id, slug, name, config, sort_order)
SELECT id, 'zen', 'Дзен', '{"primary_color":"#2E7D32","secondary_color":"#E8F5E9","accent_color":"#1B5E20","text_color":"#212121","text_color_light":"#FFFFFF","bg_color":"#FFFFFF","badge_bg":"#2E7D32","badge_text":"#FFFFFF","button_bg":"#2E7D32","button_text":"#FFFFFF","card_bg":"#E8F5E9","gradient":"linear-gradient(135deg, #2E7D32 0%, #66BB6A 100%)","icon_set":"massage_zen"}', 20
FROM promo_categories WHERE slug = 'massage';
INSERT OR IGNORE INTO promo_styles (category_id, slug, name, config, sort_order)
SELECT id, 'spa', 'Спа', '{"primary_color":"#00695C","secondary_color":"#E0F2F1","accent_color":"#004D40","text_color":"#212121","text_color_light":"#FFFFFF","bg_color":"#FFFFFF","badge_bg":"#00695C","badge_text":"#FFFFFF","button_bg":"#00695C","button_text":"#FFFFFF","card_bg":"#E0F2F1","gradient":"linear-gradient(135deg, #00695C 0%, #26A69A 100%)","icon_set":"massage_spa"}', 30
FROM promo_categories WHERE slug = 'massage';

INSERT OR IGNORE INTO promo_styles (category_id, slug, name, config, sort_order)
SELECT id, 'blue', 'Синий', '{"primary_color":"#1565C0","secondary_color":"#E3F2FD","accent_color":"#0D47A1","text_color":"#212121","text_color_light":"#FFFFFF","bg_color":"#FFFFFF","badge_bg":"#1565C0","badge_text":"#FFFFFF","button_bg":"#1565C0","button_text":"#FFFFFF","card_bg":"#E3F2FD","gradient":"linear-gradient(135deg, #1565C0 0%, #42A5F5 100%)","icon_set":"tutor_blue"}', 10
FROM promo_categories WHERE slug = 'tutor';
INSERT OR IGNORE INTO promo_styles (category_id, slug, name, config, sort_order)
SELECT id, 'academic', 'Академический', '{"primary_color":"#37474F","secondary_color":"#ECEFF1","accent_color":"#263238","text_color":"#212121","text_color_light":"#FFFFFF","bg_color":"#FFFFFF","badge_bg":"#37474F","badge_text":"#FFFFFF","button_bg":"#37474F","button_text":"#FFFFFF","card_bg":"#ECEFF1","gradient":"linear-gradient(135deg, #37474F 0%, #607D8B 100%)","icon_set":"tutor_academic"}', 20
FROM promo_categories WHERE slug = 'tutor';
INSERT OR IGNORE INTO promo_styles (category_id, slug, name, config, sort_order)
SELECT id, 'creative', 'Творческий', '{"primary_color":"#F57C00","secondary_color":"#FFF3E0","accent_color":"#E65100","text_color":"#212121","text_color_light":"#FFFFFF","bg_color":"#FFFFFF","badge_bg":"#F57C00","badge_text":"#FFFFFF","button_bg":"#F57C00","button_text":"#FFFFFF","card_bg":"#FFF3E0","gradient":"linear-gradient(135deg, #F57C00 0%, #FFB74D 100%)","icon_set":"tutor_creative"}', 30
FROM promo_categories WHERE slug = 'tutor';

INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Приеду вовремя', '⏰', 10 FROM promo_categories WHERE slug = 'cleaning';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Свои средства и инвентарь', '🧴', 20 FROM promo_categories WHERE slug = 'cleaning';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Напоминание о следующей уборке', '🔔', 30 FROM promo_categories WHERE slug = 'cleaning';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Безопасные и экологичные средства', '🌿', 40 FROM promo_categories WHERE slug = 'cleaning';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Фотоотчёт после уборки', '📸', 50 FROM promo_categories WHERE slug = 'cleaning';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Опыт более 3 лет', '⭐', 60 FROM promo_categories WHERE slug = 'cleaning';

INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Точная стрижка', '✂️', 10 FROM promo_categories WHERE slug = 'barber';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Премиальная косметика', '💈', 20 FROM promo_categories WHERE slug = 'barber';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Хорошая запись без задержки', '⏰', 30 FROM promo_categories WHERE slug = 'barber';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Стерильный инструмент', '🧼', 40 FROM promo_categories WHERE slug = 'barber';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Консультация по стилю', '💡', 50 FROM promo_categories WHERE slug = 'barber';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Удобное расположение', '📍', 60 FROM promo_categories WHERE slug = 'barber';

INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Стерильность инструментов', '🧼', 10 FROM promo_categories WHERE slug = 'manicure';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Качественные материалы', '💅', 20 FROM promo_categories WHERE slug = 'manicure';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Стойкое покрытие', '✨', 30 FROM promo_categories WHERE slug = 'manicure';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Удобное время записи', '⏰', 40 FROM promo_categories WHERE slug = 'manicure';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Индивидуальный подход', '💗', 50 FROM promo_categories WHERE slug = 'manicure';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Уютная атмосфера', '🕯️', 60 FROM promo_categories WHERE slug = 'manicure';

INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Опыт от 5 лет', '⭐', 10 FROM promo_categories WHERE slug = 'massage';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Индивидуальный подбор техники', '🤲', 20 FROM promo_categories WHERE slug = 'massage';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Удобное время записи', '⏰', 30 FROM promo_categories WHERE slug = 'massage';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Напоминание о визите', '🔔', 40 FROM promo_categories WHERE slug = 'massage';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Расслабляющая атмосфера', '🕯️', 50 FROM promo_categories WHERE slug = 'massage';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Работа с проблемными зонами', '💪', 60 FROM promo_categories WHERE slug = 'massage';

INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Индивидуальная программа', '📚', 10 FROM promo_categories WHERE slug = 'tutor';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Понятное объяснение', '💡', 20 FROM promo_categories WHERE slug = 'tutor';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Подготовка к экзаменам', '🎯', 30 FROM promo_categories WHERE slug = 'tutor';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Гибкий график', '⏰', 40 FROM promo_categories WHERE slug = 'tutor';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Домашние задания с проверкой', '✏️', 50 FROM promo_categories WHERE slug = 'tutor';
INSERT OR IGNORE INTO promo_advantages (category_id, text, icon, sort_order)
SELECT id, 'Подбор материалов', '📖', 60 FROM promo_categories WHERE slug = 'tutor';
