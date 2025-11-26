-- Add archived field to users table
ALTER TABLE users ADD COLUMN archived BOOLEAN DEFAULT FALSE;

-- Add archived field to pets table
ALTER TABLE pets ADD COLUMN archived BOOLEAN DEFAULT FALSE;

-- Add archived_at timestamp fields for tracking when items were archived
ALTER TABLE users ADD COLUMN archived_at TIMESTAMP NULL;
ALTER TABLE pets ADD COLUMN archived_at TIMESTAMP NULL;