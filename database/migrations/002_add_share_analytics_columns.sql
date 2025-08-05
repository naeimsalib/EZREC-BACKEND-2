-- Migration: Add analytics and tracking columns to shared_links table
-- This adds the missing columns needed for enhanced share link features

-- Add new columns for analytics and tracking
ALTER TABLE shared_links 
ADD COLUMN IF NOT EXISTS total_downloads INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_downloaded TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS last_download_ip INET,
ADD COLUMN IF NOT EXISTS last_download_user_agent TEXT,
ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMP WITH TIME ZONE;

-- Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_shared_links_user_id ON shared_links(user_id);
CREATE INDEX IF NOT EXISTS idx_shared_links_created_at ON shared_links(created_at);
CREATE INDEX IF NOT EXISTS idx_shared_links_expires_at ON shared_links(expires_at);
CREATE INDEX IF NOT EXISTS idx_shared_links_revoked ON shared_links(revoked);

-- Add comments for documentation
COMMENT ON COLUMN shared_links.total_downloads IS 'Total number of downloads for this share link';
COMMENT ON COLUMN shared_links.last_downloaded IS 'Timestamp of the last download';
COMMENT ON COLUMN shared_links.last_download_ip IS 'IP address of the last download';
COMMENT ON COLUMN shared_links.last_download_user_agent IS 'User agent of the last download';
COMMENT ON COLUMN shared_links.revoked_at IS 'Timestamp when the link was revoked';

-- Verify the migration
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'shared_links' 
ORDER BY ordinal_position; 