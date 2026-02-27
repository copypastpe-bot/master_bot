-- Migration 001: Initial schema
-- Master CRM Bot

CREATE TABLE IF NOT EXISTS masters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id           BIGINT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    sphere          TEXT,
    socials         TEXT,
    contacts        TEXT,
    work_hours      TEXT,
    invite_token    TEXT UNIQUE NOT NULL,
    bonus_enabled   BOOLEAN DEFAULT TRUE,
    bonus_rate      REAL DEFAULT 5.0,
    bonus_max_spend REAL DEFAULT 50.0,
    bonus_birthday  INTEGER DEFAULT 300,
    gc_connected    BOOLEAN DEFAULT FALSE,
    gc_credentials  TEXT,                    -- JSON строка с токеном GC
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clients (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id           BIGINT UNIQUE,
    name            TEXT NOT NULL,
    phone           TEXT,
    birthday        DATE,
    registered_via  INTEGER REFERENCES masters(id),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS master_clients (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id       INTEGER NOT NULL REFERENCES masters(id),
    client_id       INTEGER NOT NULL REFERENCES clients(id),
    bonus_balance   INTEGER DEFAULT 0,
    total_spent     INTEGER DEFAULT 0,
    note            TEXT,
    first_visit     TIMESTAMP,
    last_visit      TIMESTAMP,
    notify_reminders BOOLEAN DEFAULT TRUE,
    notify_marketing BOOLEAN DEFAULT TRUE,
    UNIQUE(master_id, client_id)
);

CREATE TABLE IF NOT EXISTS services (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id       INTEGER NOT NULL REFERENCES masters(id),
    name            TEXT NOT NULL,
    price           INTEGER,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id       INTEGER NOT NULL REFERENCES masters(id),
    client_id       INTEGER NOT NULL REFERENCES clients(id),
    address         TEXT,
    scheduled_at    TIMESTAMP,
    status          TEXT DEFAULT 'new',
    payment_type    TEXT,
    amount_total    INTEGER,
    bonus_accrued   INTEGER DEFAULT 0,
    bonus_spent     INTEGER DEFAULT 0,
    cancel_reason   TEXT,
    gc_event_id     TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    done_at         TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    service_id      INTEGER REFERENCES services(id),
    name            TEXT NOT NULL,
    price           INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS bonus_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id       INTEGER NOT NULL REFERENCES masters(id),
    client_id       INTEGER NOT NULL REFERENCES clients(id),
    order_id        INTEGER REFERENCES orders(id),
    type            TEXT NOT NULL,
    amount          INTEGER NOT NULL,
    comment         TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS campaigns (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id       INTEGER NOT NULL REFERENCES masters(id),
    type            TEXT NOT NULL,
    title           TEXT,
    text            TEXT NOT NULL,
    active_from     DATE,
    active_to       DATE,
    segment         TEXT DEFAULT 'all',
    sent_at         TIMESTAMP,
    sent_count      INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inbound_requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id       INTEGER NOT NULL REFERENCES masters(id),
    client_id       INTEGER NOT NULL REFERENCES clients(id),
    type            TEXT NOT NULL,
    text            TEXT,
    service_name    TEXT,
    file_id         TEXT,
    is_read         BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_orders_master_scheduled ON orders(master_id, scheduled_at);
CREATE INDEX IF NOT EXISTS idx_orders_master_status ON orders(master_id, status);
CREATE INDEX IF NOT EXISTS idx_master_clients_master ON master_clients(master_id);
CREATE INDEX IF NOT EXISTS idx_bonus_log_master_client ON bonus_log(master_id, client_id);
CREATE INDEX IF NOT EXISTS idx_clients_phone ON clients(phone);
CREATE INDEX IF NOT EXISTS idx_clients_tg_id ON clients(tg_id);
CREATE INDEX IF NOT EXISTS idx_services_master ON services(master_id, is_active);
CREATE INDEX IF NOT EXISTS idx_campaigns_master ON campaigns(master_id, active_to);
