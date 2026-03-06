-- Migration 004: Add client_confirmed field to orders
ALTER TABLE orders ADD COLUMN client_confirmed BOOLEAN DEFAULT FALSE;
