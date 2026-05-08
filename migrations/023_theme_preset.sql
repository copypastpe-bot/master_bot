-- Migration 023: Add color theme preset for master Mini App
ALTER TABLE masters ADD COLUMN theme_preset TEXT DEFAULT 'ocean';
