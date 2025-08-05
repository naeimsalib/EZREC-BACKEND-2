#!/usr/bin/env python3
import os
import sys
sys.path.append("/opt/ezrec-backend/backend")
from video_worker import fetch_user_media, download_if_needed, MEDIA_CACHE_DIR

user_id = os.environ.get("USER_ID")
if not user_id:
    print("USER_ID not set in environment")
    sys.exit(1)

intro_url, logo_url, sponsor_urls = fetch_user_media(user_id)
user_media_dir = MEDIA_CACHE_DIR / user_id
user_media_dir.mkdir(parents=True, exist_ok=True)
intro_path = user_media_dir / "intro.mp4"
logo_path = user_media_dir / "logo.png"
sponsor_paths = [user_media_dir / f"sponsor_logo{i+1}.png" for i in range(3)]

def try_download(url, path):
    try:
        print(f"Downloading {url} to {path} ...")
        download_if_needed(url, path)
        print(f"Exists after download: {path.exists()}")
        if path.exists():
            print(f"File size: {path.stat().st_size} bytes")
    except Exception as e:
        print(f"Error downloading {url}: {e}")

if intro_url:
    try_download(intro_url, intro_path)
if logo_url:
    try_download(logo_url, logo_path)
for i, sponsor_url in enumerate(sponsor_urls):
    if sponsor_url:
        try_download(sponsor_url, sponsor_paths[i])

print("User media cache directory contents:")
for f in user_media_dir.iterdir():
    print(f" - {f}") 