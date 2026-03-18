-- Migration 003: Add currency field to masters
ALTER TABLE masters ADD COLUMN currency TEXT DEFAULT 'RUB';
