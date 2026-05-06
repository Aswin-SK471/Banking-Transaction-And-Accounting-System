-- Migration: Add Extended User Information
USE banking_system;

-- Add new columns, initially without NOT NULL constraint on phone to allow updating existing rows
ALTER TABLE users
ADD COLUMN gmail VARCHAR(100) UNIQUE,
ADD COLUMN aadhar_number VARCHAR(12) UNIQUE,
ADD COLUMN phone VARCHAR(15);

-- Populate existing rows with dummy data so they don't violate constraints
-- We use user_id to ensure the UNIQUE constraints on gmail and aadhar are satisfied for existing rows
UPDATE users SET 
    gmail = CONCAT('user', user_id, '@gmail.com'),
    aadhar_number = LPAD(user_id, 12, '0'),
    phone = '0000000000'
WHERE gmail IS NULL;

-- Now apply the NOT NULL constraint on phone
ALTER TABLE users
MODIFY COLUMN phone VARCHAR(15) NOT NULL;

-- Add the CHECK constraint for Aadhar length
ALTER TABLE users
ADD CONSTRAINT chk_aadhar CHECK (LENGTH(aadhar_number) = 12);
