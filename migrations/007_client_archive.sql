-- migrations/007_client_archive.sql
ALTER TABLE master_clients ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;
