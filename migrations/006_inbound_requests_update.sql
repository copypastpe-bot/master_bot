-- Extend inbound_requests for master mini app requests module
ALTER TABLE inbound_requests ADD COLUMN notification_message_id BIGINT;

-- Explicit status lifecycle for requests: new | closed
-- Keep is_read for backward compatibility.
ALTER TABLE inbound_requests ADD COLUMN status TEXT DEFAULT 'new';
