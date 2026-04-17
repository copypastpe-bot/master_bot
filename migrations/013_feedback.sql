-- Migration 013: post-order feedback

ALTER TABLE orders ADD COLUMN feedback_sent BOOLEAN DEFAULT FALSE;
ALTER TABLE orders ADD COLUMN rating INTEGER;

ALTER TABLE masters ADD COLUMN feedback_delay_hours INTEGER DEFAULT 3;
ALTER TABLE masters ADD COLUMN feedback_message TEXT;
ALTER TABLE masters ADD COLUMN feedback_reply_5 TEXT;
ALTER TABLE masters ADD COLUMN review_buttons TEXT;
