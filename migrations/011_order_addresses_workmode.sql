-- Order flow improvements: work mode, addresses, completion comment

ALTER TABLE masters ADD COLUMN work_mode TEXT DEFAULT 'travel';
ALTER TABLE masters ADD COLUMN work_address_default TEXT;

ALTER TABLE orders ADD COLUMN note TEXT;

CREATE TABLE IF NOT EXISTS client_addresses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id       INTEGER NOT NULL REFERENCES masters(id),
    client_id       INTEGER NOT NULL REFERENCES clients(id),
    label           TEXT,
    address         TEXT NOT NULL,
    is_default      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(master_id, client_id, address)
);

CREATE INDEX IF NOT EXISTS idx_client_addresses_master_client
    ON client_addresses(master_id, client_id, is_default DESC, created_at DESC);
