# video_worker.py - Updated version with retry and file existence checks

import os
import time
import subprocess
from pathlib import Path
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
import shutil
import uuid
import json

# Load .env for manual runs, but do not override systemd env vars
load_dotenv("/opt/ezrec-backend/.env", override=False)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
USER_ID = os.getenv("USER_ID")
CAMERA_ID = os.getenv("CAMERA_ID")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

RECORDINGS_DIR = Path("/opt/ezrec-backend/recordings")
PROCESSED_DIR = Path("/opt/ezrec-backend/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

BUCKET_NAME = "videos"
LOCK_EXTENSION = ".lock"
PROCESSED_EXTENSION = ".done"


def _log(message):
    print(f"[video_worker] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")


def _get_video_duration(path: Path) -> float:
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path)
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return float(result.stdout)
    except Exception as e:
        _log(f"Failed to get duration: {e}")
        return 0.0


def _upload_video(user_id: str, file_path: Path):
    remote_path = f"{user_id}/{file_path.name}"
    with open(file_path, 'rb') as f:
        res = supabase.storage.from_(BUCKET_NAME).upload(remote_path, f, file_options={"content-type": "video/mp4"})
    if res.get("error"):
        raise RuntimeError(f"Upload failed: {res['error']}")
    return supabase.storage.from_(BUCKET_NAME).get_public_url(remote_path)


def _process_video(raw_file: Path, user_id: str) -> Path:
    output_file = PROCESSED_DIR / raw_file.name
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", str(raw_file),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            str(output_file)
        ], check=True)
        _log(f"✅ FFmpeg processed: {output_file.name}")
    except subprocess.CalledProcessError:
        _log(f"⚠️ FFmpeg failed, copying raw file")
        shutil.copy(raw_file, output_file)
    return output_file


def main():
    _log("Worker started")
    while True:
        for date_folder in RECORDINGS_DIR.glob("*/"):
            for video_file in date_folder.glob("*.mp4"):
                lock_file = video_file.with_suffix(LOCK_EXTENSION)
                done_file = video_file.with_suffix(PROCESSED_EXTENSION)
                if done_file.exists():
                    continue
                if lock_file.exists():
                    continue

                # Wait and retry if file doesn't exist
                retries = 3
                while retries > 0 and not video_file.exists():
                    _log(f"⏳ Waiting for {video_file} to appear...")
                    time.sleep(5)
                    retries -= 1
                if not video_file.exists():
                    _log(f"❌ File missing: {video_file}")
                    continue

                try:
                    lock_file.touch()
                    metadata_path = video_file.with_suffix(".json")
                    if metadata_path.exists():
                        with open(metadata_path) as f:
                            meta = json.load(f)
                    else:
                        _log(f"⚠️ No metadata found for {video_file.name}")
                        continue

                    user_id = meta.get("user_id")
                    duration = _get_video_duration(video_file)

                    processed = _process_video(video_file, user_id)
                    public_url = _upload_video(user_id, processed)

                    supabase.table("videos").insert({
                        "user_id": user_id,
                        "video_url": public_url,
                        "date": date_folder.name,
                        "recording_id": video_file.stem,
                        "duration_seconds": duration
                    }).execute()

                    done_file.touch()
                    _log(f"✅ Uploaded: {public_url}")
                except Exception as e:
                    _log(f"🔥 Error: {e}")
                finally:
                    if lock_file.exists():
                        lock_file.unlink()
        time.sleep(15)


if __name__ == "__main__":
    main()
