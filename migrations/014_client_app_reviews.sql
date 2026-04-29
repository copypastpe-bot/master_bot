-- Migration 014: client Mini App reviews and notification settings

CREATE TABLE IF NOT EXISTS reviews (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id       INTEGER NOT NULL REFERENCES masters(id),
    client_id       INTEGER NOT NULL REFERENCES clients(id),
    order_id        INTEGER REFERENCES orders(id),
    rating          INTEGER,
    text            TEXT NOT NULL,
    is_visible      BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(order_id)
);

CREATE INDEX IF NOT EXISTS idx_reviews_master
ON reviews(master_id, is_visible, created_at DESC);

ALTER TABLE master_clients ADD COLUMN notify_bonuses BOOLEAN DEFAULT TRUE;
