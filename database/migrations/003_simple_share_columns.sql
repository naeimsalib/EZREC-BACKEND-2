-- Simple Migration: Add only essential columns for basic share link functionality
-- This is a minimal version that adds just the columns needed for the core features

-- Add only the essential columns
ALTER TABLE shared_links 
ADD COLUMN IF NOT EXISTS total_downloads INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMP WITH TIME ZONE;

-- Add basic index for performance
CREATE INDEX IF NOT EXISTS idx_shared_links_user_id ON shared_links(user_id);

-- Verify the migration
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'shared_links' 
ORDER BY ordinal_position; 