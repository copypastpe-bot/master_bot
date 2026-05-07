-- Migration 020: Normalize master categories into dictionary + links.

CREATE TABLE IF NOT EXISTS master_categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slug        TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    icon        TEXT,
    sort_order  INTEGER DEFAULT 0,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO master_categories (slug, name, icon, sort_order) VALUES
    ('cleaning',         'Клининг',                       '🧹', 1),
    ('dry_cleaning',     'Химчистка мебели и ковров',     '🛋️', 2),
    ('barber',           'Парикмахер и барбер',           '✂️', 3),
    ('beauty',           'Маникюр и бьюти-услуги',        '💅', 4),
    ('grooming',         'Груминг и животные',            '🐾', 5),
    ('massage',          'Массаж',                        '💆', 6),
    ('appliance_repair', 'Ремонт бытовой техники',        '🔧', 7),
    ('handyman',         'Мастер на час, мелкий ремонт',  '🔨', 8),
    ('tutor',            'Репетитор',                     '📚', 9),
    ('photographer',     'Фотограф и видеограф',          '📷', 10),
    ('psychologist',     'Психолог',                      '🧠', 11),
    ('gardener',         'Садовник',                      '🌱', 12),
    ('other',            'Другое',                        '📌', 13);

CREATE TABLE IF NOT EXISTS master_category_links (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id   INTEGER NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES master_categories(id) ON DELETE CASCADE,
    custom_name TEXT,
    sort_order  INTEGER DEFAULT 0,
    UNIQUE(master_id, category_id)
);

CREATE INDEX IF NOT EXISTS idx_mcl_master ON master_category_links(master_id);
CREATE INDEX IF NOT EXISTS idx_mcl_category ON master_category_links(category_id);
