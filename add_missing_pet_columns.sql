-- Add missing columns to pets table for Supabase compatibility

-- Add for_adoption column
ALTER TABLE pets ADD COLUMN IF NOT EXISTS for_adoption BOOLEAN DEFAULT FALSE;

-- Add lost column
ALTER TABLE pets ADD COLUMN IF NOT EXISTS lost BOOLEAN DEFAULT FALSE;

-- Add registered_on timestamp
ALTER TABLE pets ADD COLUMN IF NOT EXISTS registered_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Add status column (if not already added)
ALTER TABLE pets ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'pending';

-- Add approved_at and approved_by columns (if not already added)
ALTER TABLE pets ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP NULL;
ALTER TABLE pets ADD COLUMN IF NOT EXISTS approved_by INTEGER NULL;

-- Add archived columns (if not already added)
ALTER TABLE pets ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT FALSE;
ALTER TABLE pets ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP NULL;