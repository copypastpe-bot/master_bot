-- Migration 005: Add description field to services
ALTER TABLE services ADD COLUMN description TEXT;
