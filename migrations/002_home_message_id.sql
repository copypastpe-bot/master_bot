-- Migration 002: Add home_message_id columns
-- For hybrid UI: Home message is edited, not recreated

ALTER TABLE masters ADD COLUMN home_message_id BIGINT;

ALTER TABLE master_clients ADD COLUMN home_message_id BIGINT;

-- Add notification settings columns to master_clients
ALTER TABLE master_clients ADD COLUMN notify_24h BOOLEAN DEFAULT TRUE;
ALTER TABLE master_clients ADD COLUMN notify_1h BOOLEAN DEFAULT TRUE;
ALTER TABLE master_clients ADD COLUMN notify_promos BOOLEAN DEFAULT TRUE;
