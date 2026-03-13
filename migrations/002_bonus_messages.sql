-- Migration 002: Bonus messages and timezone
-- Adds welcome bonus, custom messages, and timezone support

ALTER TABLE masters ADD COLUMN bonus_welcome INTEGER DEFAULT 0;
ALTER TABLE masters ADD COLUMN timezone TEXT DEFAULT 'Europe/Moscow';
ALTER TABLE masters ADD COLUMN welcome_message TEXT;
ALTER TABLE masters ADD COLUMN welcome_photo_id TEXT;
ALTER TABLE masters ADD COLUMN birthday_message TEXT;
ALTER TABLE masters ADD COLUMN birthday_photo_id TEXT;
