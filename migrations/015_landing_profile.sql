-- Migration 015: landing profile — avatar, about, portfolio, show_on_landing
-- Note: reviews table already created in migration 014

ALTER TABLE masters ADD COLUMN about TEXT;
ALTER TABLE masters ADD COLUMN avatar_file_id TEXT;

ALTER TABLE services ADD COLUMN show_on_landing BOOLEAN DEFAULT 1;

CREATE TABLE IF NOT EXISTS master_portfolio (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id   INTEGER NOT NULL REFERENCES masters(id),
    file_id     TEXT NOT NULL,
    sort_order  INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_master_portfolio_master ON master_portfolio(master_id, sort_order);
