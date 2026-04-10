-- Structured contact fields for master profile
-- Keep legacy contacts/socials/work_hours for backward compatibility.

ALTER TABLE masters ADD COLUMN phone TEXT;
ALTER TABLE masters ADD COLUMN telegram TEXT;
ALTER TABLE masters ADD COLUMN instagram TEXT;
ALTER TABLE masters ADD COLUMN website TEXT;
ALTER TABLE masters ADD COLUMN contact_address TEXT;
