-- Store all media attachments for inbound requests (multi-photo/video support)
CREATE TABLE IF NOT EXISTS inbound_request_media (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id              INTEGER NOT NULL REFERENCES inbound_requests(id) ON DELETE CASCADE,
    file_id                 TEXT NOT NULL,
    media_type              TEXT NOT NULL,
    position                INTEGER DEFAULT 0,
    notification_message_id BIGINT,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(request_id, file_id)
);

CREATE INDEX IF NOT EXISTS idx_inbound_request_media_request
    ON inbound_request_media(request_id);

-- Backfill first media from legacy single-file columns.
INSERT OR IGNORE INTO inbound_request_media (request_id, file_id, media_type, position)
SELECT
    ir.id,
    ir.file_id,
    CASE
        WHEN ir.media_type IS NULL OR ir.media_type = '' THEN 'photo'
        ELSE ir.media_type
    END,
    0
FROM inbound_requests ir
WHERE ir.file_id IS NOT NULL;
