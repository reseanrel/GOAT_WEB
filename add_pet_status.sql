-- Add status field to pets table for approval workflow
ALTER TABLE pets ADD COLUMN status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending';

-- Add approval timestamp fields
ALTER TABLE pets ADD COLUMN approved_at TIMESTAMP NULL;
ALTER TABLE pets ADD COLUMN approved_by INT NULL;

-- Add foreign key constraint for approved_by
ALTER TABLE pets ADD CONSTRAINT fk_pets_approved_by FOREIGN KEY (approved_by) REFERENCES users(id);