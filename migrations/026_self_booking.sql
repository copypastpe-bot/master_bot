-- Self-booking feature schema (see docs/plans/2026-05-25-self-booking-design.md).

-- 1. Service duration drives slot-grid math and overlap detection.
-- 60 minutes is a reasonable starting estimate; masters tune per service.
ALTER TABLE services ADD COLUMN duration_minutes INTEGER NOT NULL DEFAULT 60;

-- 2. Booking metadata on the shared orders table — no separate bookings entity.
-- source distinguishes manual master entries ('manual') from self-bookings
-- via public link ('public') or client_bot ('telegram_bot').
ALTER TABLE orders ADD COLUMN source TEXT NOT NULL DEFAULT 'manual';
-- cancel_token: UUID handed back to the client so they can revisit/cancel
-- their booking via /b/{token} without any Telegram identity.
ALTER TABLE orders ADD COLUMN cancel_token TEXT;
-- duration_minutes: snapshot of services.duration_minutes at booking time.
-- Storing on the order itself means a later edit of the service duration
-- does not retroactively shift past bookings (or break overlap math).
ALTER TABLE orders ADD COLUMN duration_minutes INTEGER;
CREATE INDEX IF NOT EXISTS idx_orders_cancel_token
    ON orders(cancel_token) WHERE cancel_token IS NOT NULL;

-- 3. Per-master self-booking settings.
ALTER TABLE masters ADD COLUMN self_booking_enabled BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE masters ADD COLUMN booking_cancel_cutoff_hours INTEGER NOT NULL DEFAULT 24;
ALTER TABLE masters ADD COLUMN booking_horizon_days INTEGER NOT NULL DEFAULT 30;

-- 4. Weekly schedule template. Multiple rows per (master, weekday) allowed
-- to support split shifts (e.g. 10:00-14:00 + 16:00-20:00 on the same day).
CREATE TABLE IF NOT EXISTS master_schedule_weekly (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id   INTEGER NOT NULL REFERENCES masters(id),
    weekday     INTEGER NOT NULL,        -- 0=Mon … 6=Sun
    start_time  TEXT NOT NULL,           -- "10:00"
    end_time    TEXT NOT NULL,           -- "18:00"
    UNIQUE(master_id, weekday, start_time)
);

-- 5. Date-level overrides:
--   kind='off'      → entire day unavailable, start_time/end_time NULL.
--   kind='override' → replaces weekly for that date; start_time/end_time required.
CREATE TABLE IF NOT EXISTS master_schedule_exceptions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id   INTEGER NOT NULL REFERENCES masters(id),
    date        TEXT NOT NULL,           -- "2026-06-15"
    kind        TEXT NOT NULL,           -- 'off' | 'override'
    start_time  TEXT,
    end_time    TEXT,
    UNIQUE(master_id, date, start_time)
);
