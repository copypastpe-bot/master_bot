-- Extend inbound_requests with booking date/time and media type
ALTER TABLE inbound_requests ADD COLUMN desired_date TEXT;
ALTER TABLE inbound_requests ADD COLUMN desired_time TEXT;
ALTER TABLE inbound_requests ADD COLUMN media_type TEXT;
