-- Enhanced Shared Links Table Migration
-- This migration adds comprehensive tracking and analytics fields to the shared_links table

-- Create the enhanced shared_links table
CREATE TABLE IF NOT EXISTS public.shared_links (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    token TEXT UNIQUE NOT NULL,
    video_key TEXT NOT NULL,
    user_id TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP WITH TIME ZONE,
    revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    
    -- Enhanced tracking fields
    total_downloads INTEGER DEFAULT 0,
    last_downloaded TIMESTAMP WITH TIME ZONE,
    last_download_ip TEXT,
    last_download_user_agent TEXT,
    
    -- Share metadata
    share_method TEXT DEFAULT 'copy_link', -- 'email', 'sms', 'copy_link', 'social'
    share_platform TEXT, -- 'web', 'mobile', 'api'
    
    -- Geographic tracking (basic)
    first_access_ip TEXT,
    first_access_user_agent TEXT,
    
    -- Analytics metadata
    first_accessed TIMESTAMP WITH TIME ZONE,
    last_referrer TEXT,
    
    -- Constraints
    CONSTRAINT shared_links_token_check CHECK (LENGTH(token) >= 32),
    CONSTRAINT shared_links_access_count_check CHECK (access_count >= 0),
    CONSTRAINT shared_links_downloads_check CHECK (total_downloads >= 0)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_shared_links_user_id ON public.shared_links(user_id);
CREATE INDEX IF NOT EXISTS idx_shared_links_video_key ON public.shared_links(video_key);
CREATE INDEX IF NOT EXISTS idx_shared_links_created_at ON public.shared_links(created_at);
CREATE INDEX IF NOT EXISTS idx_shared_links_expires_at ON public.shared_links(expires_at);
CREATE INDEX IF NOT EXISTS idx_shared_links_revoked ON public.shared_links(revoked);
CREATE INDEX IF NOT EXISTS idx_shared_links_access_count ON public.shared_links(access_count);

-- Add comments for documentation
COMMENT ON TABLE public.shared_links IS 'Enhanced table for tracking video share links with comprehensive analytics';
COMMENT ON COLUMN public.shared_links.token IS 'Unique token for the share link';
COMMENT ON COLUMN public.shared_links.video_key IS 'S3 key of the shared video';
COMMENT ON COLUMN public.shared_links.user_id IS 'ID of the user who created the share link';
COMMENT ON COLUMN public.shared_links.access_count IS 'Number of times this link has been accessed';
COMMENT ON COLUMN public.shared_links.total_downloads IS 'Number of times the video has been downloaded';
COMMENT ON COLUMN public.shared_links.share_method IS 'Method used to share the link (email, sms, copy_link, social)';
COMMENT ON COLUMN public.shared_links.share_platform IS 'Platform where the link was created (web, mobile, api)';

-- Create a view for popular videos analytics
CREATE OR REPLACE VIEW public.popular_videos AS
SELECT 
    video_key,
    COUNT(*) as share_count,
    SUM(access_count) as total_views,
    SUM(total_downloads) as total_downloads,
    MAX(created_at) as last_shared,
    AVG(access_count) as avg_views_per_share
FROM public.shared_links 
WHERE revoked = FALSE 
  AND (expires_at IS NULL OR expires_at > NOW())
GROUP BY video_key
ORDER BY total_views DESC;

-- Create a view for user analytics
CREATE OR REPLACE VIEW public.user_share_analytics AS
SELECT 
    user_id,
    COUNT(*) as total_links_created,
    COUNT(CASE WHEN revoked = FALSE AND (expires_at IS NULL OR expires_at > NOW()) THEN 1 END) as active_links,
    SUM(access_count) as total_views_generated,
    SUM(total_downloads) as total_downloads_generated,
    MAX(created_at) as last_link_created,
    AVG(access_count) as avg_views_per_link
FROM public.shared_links 
GROUP BY user_id
ORDER BY total_views_generated DESC;

-- Create a function to clean up expired links
CREATE OR REPLACE FUNCTION public.cleanup_expired_links()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM public.shared_links 
    WHERE expires_at < NOW() 
      AND revoked = FALSE;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create a function to get link statistics
CREATE OR REPLACE FUNCTION public.get_link_stats(p_link_token TEXT)
RETURNS TABLE(
    token TEXT,
    video_key TEXT,
    access_count INTEGER,
    total_downloads INTEGER,
    created_at TIMESTAMP WITH TIME ZONE,
    last_accessed TIMESTAMP WITH TIME ZONE,
    is_expired BOOLEAN,
    is_revoked BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        sl.token,
        sl.video_key,
        sl.access_count,
        sl.total_downloads,
        sl.created_at,
        sl.last_accessed,
        (sl.expires_at < NOW()) as is_expired,
        sl.revoked as is_revoked
    FROM public.shared_links sl
    WHERE sl.token = p_link_token;
END;
$$ LANGUAGE plpgsql;

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON public.shared_links TO authenticated;
GRANT SELECT ON public.popular_videos TO authenticated;
GRANT SELECT ON public.user_share_analytics TO authenticated;
GRANT EXECUTE ON FUNCTION public.cleanup_expired_links() TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_link_stats(TEXT) TO authenticated;

-- Insert sample data for testing (optional)
-- INSERT INTO public.shared_links (token, video_key, user_id, expires_at) 
-- VALUES 
--     ('sample_token_1', 'user123/video1.mp4', 'user123', NOW() + INTERVAL '7 days'),
--     ('sample_token_2', 'user123/video2.mp4', 'user123', NOW() + INTERVAL '7 days'); 