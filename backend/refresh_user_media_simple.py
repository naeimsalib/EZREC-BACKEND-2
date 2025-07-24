#!/usr/bin/env python3
"""
Simplified user media refresh script for deployment
- Doesn't import video_worker.py to avoid logging permission issues
- Directly implements the media fetching and downloading logic
"""
import os
import sys
import requests
import boto3
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Load environment
load_dotenv("/opt/ezrec-backend/.env", override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MEDIA_CACHE_DIR = Path("/opt/ezrec-backend/media_cache")

def s3_signed_url(bucket, key, region, expires=3600):
    """Generate signed S3 URL"""
    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=region
    )
    return s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={'Bucket': bucket, 'Key': key},
        ExpiresIn=expires
    )

def fetch_user_media(user_id: str):
    """Fetch user media from Supabase"""
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        res = supabase.table("user_settings").select("*").eq("user_id", user_id).single().execute()
        if res.data:
            intro_path = res.data.get("intro_video_path")
            logo_path = res.data.get("logo_path")
            sponsor1 = res.data.get("sponsor_logo1_path")
            sponsor2 = res.data.get("sponsor_logo2_path")
            sponsor3 = res.data.get("sponsor_logo3_path")
            
            bucket = os.getenv("AWS_USER_MEDIA_BUCKET") or os.getenv("AWS_S3_BUCKET")
            region = os.getenv("AWS_REGION", "us-east-1")
            
            def s3_url(path):
                if not path:
                    return None
                if path.startswith("http"):
                    return path
                return s3_signed_url(bucket, path, region)
            
            intro_url = s3_url(intro_path)
            logo_url = s3_url(logo_path)
            sponsor_urls = [s3_url(s) for s in [sponsor1, sponsor2, sponsor3] if s]
            return intro_url, logo_url, sponsor_urls
        return None, None, []
    except Exception as e:
        print(f"Error fetching user media: {e}")
        return None, None, []

def download_if_needed(url, path: Path):
    """Download file if it doesn't exist"""
    if url and not path.exists():
        try:
            print(f"Downloading {url} to {path} ...")
            r = requests.get(url, stream=True, timeout=30)
            if r.status_code == 200:
                with open(path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"Exists after download: {path.exists()}")
                if path.exists():
                    print(f"File size: {path.stat().st_size} bytes")
            else:
                print(f"Failed to download {url}: HTTP {r.status_code}")
        except Exception as e:
            print(f"Failed to download {url}: {e}")
            if path.exists():
                path.unlink()
    return path if path.exists() else None

def main():
    user_id = os.environ.get("USER_ID")
    if not user_id:
        print("USER_ID not set in environment")
        sys.exit(1)

    print(f"Refreshing media for user: {user_id}")
    
    intro_url, logo_url, sponsor_urls = fetch_user_media(user_id)
    user_media_dir = MEDIA_CACHE_DIR / user_id
    user_media_dir.mkdir(parents=True, exist_ok=True)
    
    intro_path = user_media_dir / "intro.mp4"
    logo_path = user_media_dir / "logo.png"
    sponsor_paths = [user_media_dir / f"sponsor_logo{i+1}.png" for i in range(3)]

    if intro_url:
        download_if_needed(intro_url, intro_path)
    if logo_url:
        download_if_needed(logo_url, logo_path)
    for i, sponsor_url in enumerate(sponsor_urls):
        if sponsor_url:
            download_if_needed(sponsor_url, sponsor_paths[i])

    print("User media cache directory contents:")
    for f in user_media_dir.iterdir():
        print(f" - {f}")

if __name__ == "__main__":
    main() 