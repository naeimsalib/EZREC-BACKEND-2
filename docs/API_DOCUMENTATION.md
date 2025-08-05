# EZREC Share Link API Documentation

## Overview
This API provides comprehensive video sharing functionality with analytics, tracking, and management capabilities.

## Base URL
```
https://api.ezrec.org
```

## Authentication
Most endpoints require user authentication. Include user credentials in request headers or body as appropriate.

## Endpoints

### 1. Create Share Link
**POST** `/share`

Creates a new share link for a video.

**Request Body:**
```json
{
  "key": "user123/2025-07-09/video.mp4",
  "user_id": "user123"
}
```

**Response:**
```json
{
  "url": "https://api.ezrec.org/share/9f0fde0f66ec4dcead99017e239735fa"
}
```

**Status Codes:**
- `200` - Share link created successfully
- `400` - Invalid request data
- `500` - Server error

---

### 2. Access Share Link
**GET** `/share/{token}`

Accesses a shared video link. Returns an HTML page with video player and download options.

**Parameters:**
- `token` (path) - The share link token

**Response:**
- `200` - HTML page with video player
- `404` - Link not found or expired
- `410` - Link has been revoked

**Features:**
- Video playback with HTML5 player
- Download tracking
- Analytics display
- Responsive design

---

### 3. Revoke Share Link
**POST** `/share/{token}/revoke`

Revokes a share link. Only the original creator can revoke the link.

**Request Body:**
```json
{
  "user_id": "user123"
}
```

**Response:**
```json
{
  "status": "revoked",
  "message": "Share link revoked successfully"
}
```

**Status Codes:**
- `200` - Link revoked successfully
- `404` - Link not found or access denied
- `500` - Server error

---

### 4. Track Download
**POST** `/share/{token}/download`

Tracks when someone downloads a video from a share link.

**Parameters:**
- `token` (path) - The share link token

**Response:**
```json
{
  "status": "download_tracked",
  "download_count": 5
}
```

**Status Codes:**
- `200` - Download tracked successfully
- `404` - Link not found
- `500` - Server error

---

### 5. Get User Analytics
**GET** `/share/analytics/{user_id}`

Gets comprehensive analytics for all share links created by a user.

**Parameters:**
- `user_id` (path) - The user ID

**Response:**
```json
{
  "total_links": 15,
  "active_links": 8,
  "total_views": 1250,
  "total_downloads": 89,
  "links": [
    {
      "token": "9f0fde0f66ec4dcead99017e239735fa",
      "video_key": "user123/video1.mp4",
      "created_at": "2025-07-10T15:30:00Z",
      "expires_at": "2025-07-17T15:30:00Z",
      "access_count": 45,
      "total_downloads": 12,
      "last_accessed": "2025-07-10T16:45:00Z",
      "revoked": false
    }
  ]
}
```

**Status Codes:**
- `200` - Analytics retrieved successfully
- `500` - Server error

---

### 6. Get Popular Videos
**GET** `/share/analytics/popular`

Gets the most popular shared videos across all users.

**Response:**
```json
{
  "popular_videos": [
    {
      "video_key": "user123/video1.mp4",
      "share_count": 5,
      "total_views": 250,
      "total_downloads": 45,
      "last_shared": "2025-07-10T15:30:00Z"
    }
  ]
}
```

**Status Codes:**
- `200` - Popular videos retrieved successfully
- `500` - Server error

---

### 7. CORS Preflight
**OPTIONS** `/share`

Handles CORS preflight requests for the share endpoint.

**Response:**
```json
{
  "message": "OK"
}
```

**Status Codes:**
- `200` - CORS headers returned

---

## Database Schema

### Shared Links Table
```sql
CREATE TABLE shared_links (
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
    total_downloads INTEGER DEFAULT 0,
    last_downloaded TIMESTAMP WITH TIME ZONE,
    last_download_ip TEXT,
    last_download_user_agent TEXT,
    share_method TEXT DEFAULT 'copy_link',
    share_platform TEXT,
    first_access_ip TEXT,
    first_access_user_agent TEXT,
    first_accessed TIMESTAMP WITH TIME ZONE,
    last_referrer TEXT
);
```

## Analytics Views

### Popular Videos View
```sql
CREATE VIEW popular_videos AS
SELECT 
    video_key,
    COUNT(*) as share_count,
    SUM(access_count) as total_views,
    SUM(total_downloads) as total_downloads,
    MAX(created_at) as last_shared,
    AVG(access_count) as avg_views_per_share
FROM shared_links 
WHERE revoked = FALSE 
  AND (expires_at IS NULL OR expires_at > NOW())
GROUP BY video_key
ORDER BY total_views DESC;
```

### User Analytics View
```sql
CREATE VIEW user_share_analytics AS
SELECT 
    user_id,
    COUNT(*) as total_links_created,
    COUNT(CASE WHEN revoked = FALSE AND (expires_at IS NULL OR expires_at > NOW()) THEN 1 END) as active_links,
    SUM(access_count) as total_views_generated,
    SUM(total_downloads) as total_downloads_generated,
    MAX(created_at) as last_link_created,
    AVG(access_count) as avg_views_per_link
FROM shared_links 
GROUP BY user_id
ORDER BY total_views_generated DESC;
```

## Error Handling

### Common Error Responses
```json
{
  "detail": "Error message description"
}
```

### Error Codes
- `400` - Bad Request (invalid data)
- `404` - Not Found (link doesn't exist)
- `410` - Gone (link expired or revoked)
- `500` - Internal Server Error

## Rate Limiting
- Share link creation: 10 requests per minute per user
- Analytics queries: 30 requests per minute per user
- Download tracking: No limit

## Security Features
- Token-based authentication for revocation
- Automatic expiration of links
- Revocation capability
- Access tracking and analytics
- CORS protection

## Usage Examples

### Frontend Integration

#### Create Share Link
```javascript
const createShareLink = async (videoKey, userId) => {
  const response = await fetch('/share', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key: videoKey, user_id: userId })
  });
  return response.json();
};
```

#### Revoke Share Link
```javascript
const revokeShareLink = async (token, userId) => {
  const response = await fetch(`/share/${token}/revoke`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId })
  });
  return response.json();
};
```

#### Get Analytics
```javascript
const getAnalytics = async (userId) => {
  const response = await fetch(`/share/analytics/${userId}`);
  return response.json();
};
```

## Environment Variables
- `SHARE_BASE_URL` - Base URL for share links (default: https://api.ezrec.org)
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` - Supabase service role key
- `AWS_S3_BUCKET` - S3 bucket for video storage

## Deployment Notes
1. Run the database migration: `database/migrations/001_enhanced_shared_links.sql`
2. Set up environment variables
3. Deploy the backend code
4. Test all endpoints with sample data 