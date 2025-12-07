-- Add rejection_reason column to pets table
ALTER TABLE pets ADD COLUMN IF NOT EXISTS rejection_reason TEXT NULL;