-- Add consent_given_at to clients table for GDPR compliance
ALTER TABLE clients ADD COLUMN consent_given_at TIMESTAMP;
