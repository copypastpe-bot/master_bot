-- Add reminder flags to orders table
ALTER TABLE orders ADD COLUMN reminder_24h_sent BOOLEAN DEFAULT FALSE;
ALTER TABLE orders ADD COLUMN reminder_1h_sent BOOLEAN DEFAULT FALSE;
