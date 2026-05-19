-- Broadcast progress: move send loop out of the HTTP request into a
-- background worker. Status flips pending -> running -> done/failed.
-- Existing rows are pre-broadcast-async and are correctly considered 'done'.
ALTER TABLE campaigns ADD COLUMN status TEXT NOT NULL DEFAULT 'done';
ALTER TABLE campaigns ADD COLUMN total_recipients INTEGER NOT NULL DEFAULT 0;
ALTER TABLE campaigns ADD COLUMN failed_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE campaigns ADD COLUMN last_progress_at TIMESTAMP;
ALTER TABLE campaigns ADD COLUMN media_path TEXT;
ALTER TABLE campaigns ADD COLUMN media_type TEXT;

-- Per-recipient queue. Seeded at campaign creation so a crashed worker
-- can resume by selecting WHERE status='pending' — no need to recompute
-- segment membership (which may shift under our feet as new orders arrive).
CREATE TABLE IF NOT EXISTS broadcast_recipients (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id  INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    client_id    INTEGER NOT NULL REFERENCES clients(id),
    tg_id        INTEGER NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',  -- pending | sent | failed | blocked
    sent_at      TIMESTAMP,
    error        TEXT
);

CREATE INDEX IF NOT EXISTS idx_broadcast_recipients_campaign_status
    ON broadcast_recipients(campaign_id, status);
