-- Create photo_emp table in cids schema
CREATE TABLE IF NOT EXISTS cids.photo_emp (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    photo_path VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create index on email for faster lookups
CREATE INDEX IF NOT EXISTS idx_photo_emp_email ON cids.photo_emp(email);

-- Add comment to table
COMMENT ON TABLE cids.photo_emp IS 'Stores employee photo paths by email';
COMMENT ON COLUMN cids.photo_emp.email IS 'Employee email address';
COMMENT ON COLUMN cids.photo_emp.photo_path IS 'Relative path to photo file in CID/photos directory';

-- Insert some test data (optional)
-- INSERT INTO cids.photo_emp (email, photo_path) VALUES 
-- ('john.doe@example.com', 'john_doe.jpg'),
-- ('jane.smith@example.com', 'jane_smith.png');