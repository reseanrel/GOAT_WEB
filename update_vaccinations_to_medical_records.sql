-- Rename vaccinations table to medical_records
ALTER TABLE vaccinations RENAME TO medical_records;

-- Add photo_url column for receipts/images
ALTER TABLE medical_records ADD COLUMN IF NOT EXISTS photo_url TEXT;

-- Rename vaccine_name to record_type
ALTER TABLE medical_records RENAME COLUMN vaccine_name TO record_type;

-- Rename date_administered to record_date
ALTER TABLE medical_records RENAME COLUMN date_administered TO record_date;

-- Rename administered_by to provider
ALTER TABLE medical_records RENAME COLUMN administered_by TO provider;

-- Add description column for additional details
ALTER TABLE medical_records ADD COLUMN IF NOT EXISTS description TEXT;