import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
USER_ID = os.getenv('USER_ID')

if not SUPABASE_URL or not SUPABASE_KEY or not USER_ID:
    print("Missing SUPABASE_URL, SUPABASE_KEY, or USER_ID in .env")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

local_path = input("Enter the path to the video file to upload: ").strip()
if not os.path.exists(local_path):
    print(f"File not found: {local_path}")
    exit(1)

remote_path = f"{USER_ID}/manual_test_upload.mp4"

with open(local_path, 'rb') as f:
    try:
        resp = supabase.storage.from_('videos').upload(remote_path, f)
        print("Upload response:", resp)
        url = supabase.storage.from_('videos').get_public_url(remote_path)
        print("Public URL:", url)
    except Exception as e:
        print("Upload failed:", e) 