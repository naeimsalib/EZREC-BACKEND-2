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
import requests
import boto3
from boto3.s3.transfer import TransferConfig

# Load .env for manual runs, but do not override systemd env vars
load_dotenv("/opt/ezrec-backend/.env", override=False)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
USER_ID = os.getenv("USER_ID")
CAMERA_ID = os.getenv("CAMERA_ID")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# S3 configuration
s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)
S3_BUCKET = os.getenv("AWS_S3_BUCKET")

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


def upload_large_file_to_s3(file_path, bucket_name, s3_key):
    config = TransferConfig(
        multipart_threshold=50 * 1024 * 1024,  # 50MB
        multipart_chunksize=10 * 1024 * 1024,  # 10MB per chunk
        use_threads=True
    )
    try:
        print(f"Uploading {file_path} to s3://{bucket_name}/{s3_key}...")
        s3 = boto3.client('s3')
        s3.upload_file(str(file_path), bucket_name, s3_key, Config=config, ExtraArgs={"ContentType": "video/mp4", "ACL": "public-read"})
        print("✅ S3 Upload completed.")
        public_url = f"https://{bucket_name}.s3.{os.getenv('AWS_REGION')}.amazonaws.com/{s3_key}"
        return public_url
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return None


def _download_if_needed(url: str, dest: Path) -> Path:
    """Download a file from a URL if it doesn't exist or is outdated."""
    if not url:
        return None
    try:
        if dest.exists():
            return dest
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            with open(dest, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            _log(f"Downloaded: {dest}")
            return dest
        else:
            _log(f"Failed to download {url}: {r.status_code}")
            return None
    except Exception as e:
        _log(f"Error downloading {url}: {e}")
        return None


def _fetch_intro_logo(user_id: str):
    """Fetch intro and logo URLs from Supabase user_settings."""
    try:
        res = supabase.table("user_settings").select("intro_video_url,logo_url").eq("user_id", user_id).single().execute()
        if res.data:
            return res.data.get("intro_video_url"), res.data.get("logo_url")
    except Exception as e:
        _log(f"Failed to fetch intro/logo: {e}")
    return None, None


def _process_video(raw_file: Path, user_id: str) -> Path:
    output_file = PROCESSED_DIR / raw_file.name
    intro_url, logo_url = _fetch_intro_logo(user_id)
    intro_path = None
    logo_path = None
    concat_list = None
    concat_output = None
    try:
        # Download intro and logo if needed
        if intro_url:
            intro_path = Path(f"/opt/ezrec-backend/media_cache/intro_{user_id}.mp4")
            _download_if_needed(intro_url, intro_path)
        if logo_url:
            logo_path = Path(f"/opt/ezrec-backend/media_cache/logo_{user_id}.png")
            _download_if_needed(logo_url, logo_path)
        # Build FFmpeg command
        if intro_path and intro_path.exists():
            # Concatenate intro + main
            concat_list = Path(f"/tmp/concat_{uuid.uuid4().hex}.txt")
            with open(concat_list, "w") as f:
                f.write(f"file '{intro_path}'\n")
                f.write(f"file '{raw_file}'\n")
            concat_output = output_file.with_suffix(".concat.mp4")
            ffmpeg_concat = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(concat_output)
            ]
            try:
                subprocess.run(ffmpeg_concat, check=True)
            except subprocess.CalledProcessError as e:
                _log(f"⚠️ FFmpeg concat failed: {e}. Trying with -an (no audio fallback)...")
                ffmpeg_concat_fallback = [
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", "-an", str(concat_output)
                ]
                subprocess.run(ffmpeg_concat_fallback, check=True)
            input_for_logo = concat_output
        else:
            input_for_logo = raw_file
        # Overlay logo if present
        if logo_path and logo_path.exists():
            ffmpeg_logo = [
                "ffmpeg", "-y", "-i", str(input_for_logo), "-i", str(logo_path),
                "-filter_complex", "overlay=W-w-10:H-h-10", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                str(output_file)
            ]
            try:
                subprocess.run(ffmpeg_logo, check=True)
            except subprocess.CalledProcessError as e:
                _log(f"⚠️ FFmpeg logo overlay failed: {e}. Trying with -an (no audio fallback)...")
                ffmpeg_logo_fallback = [
                    "ffmpeg", "-y", "-i", str(input_for_logo), "-i", str(logo_path),
                    "-filter_complex", "overlay=W-w-10:H-h-10", "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-an",
                    str(output_file)
                ]
                subprocess.run(ffmpeg_logo_fallback, check=True)
            if input_for_logo != raw_file and input_for_logo.exists():
                input_for_logo.unlink()  # cleanup temp concat file
        else:
            # No logo, just re-encode (or copy if already processed)
            if input_for_logo != output_file:
                try:
                    subprocess.run([
                        "ffmpeg", "-y", "-i", str(input_for_logo),
                        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                        str(output_file)
                    ], check=True)
                except subprocess.CalledProcessError as e:
                    _log(f"⚠️ FFmpeg re-encode failed: {e}. Trying with -an (no audio fallback)...")
                    subprocess.run([
                        "ffmpeg", "-y", "-i", str(input_for_logo),
                        "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-an",
                        str(output_file)
                    ], check=True)
                if input_for_logo != raw_file and input_for_logo.exists():
                    input_for_logo.unlink()
        _log(f"✅ FFmpeg processed: {output_file.name}")
    except subprocess.CalledProcessError as e:
        _log(f"⚠️ FFmpeg failed: {e}")
        shutil.copy(raw_file, output_file)
    except Exception as e:
        _log(f"🔥 Video processing error: {e}")
        shutil.copy(raw_file, output_file)
    finally:
        # Clean up temp concat file if it exists
        if concat_list and concat_list.exists():
            concat_list.unlink()
        if concat_output and concat_output.exists() and concat_output != output_file:
            try:
                concat_output.unlink()
            except Exception:
                pass
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
                        try:
                            with open(metadata_path) as f:
                                meta = json.load(f)
                        except Exception as e:
                            _log(f"⚠️ Failed to load metadata JSON for {video_file.name}: {e}")
                            continue
                    else:
                        _log(f"⚠️ No metadata found for {video_file.name}")
                        continue

                    user_id = meta.get("user_id")
                    duration = _get_video_duration(video_file)

                    processed = _process_video(video_file, user_id)
                    # Add check: skip upload if processed file doesn't exist
                    if not processed.exists():
                        _log(f"❌ Processed video not found, skipping upload: {processed}")
                        continue
                    # After processing, update booking status to 'video_processed'
                    try:
                        booking_id = meta.get("booking_id")
                        if booking_id:
                            supabase.table("bookings").update({"status": "video_processed"}).eq("id", booking_id).execute()
                            _log(f"Booking {booking_id} status set to 'video_processed'")
                    except Exception as e:
                        _log(f"Failed to update booking status to video_processed: {e}")
                    # Robust upload with logging
                    try:
                        s3_key = f"{user_id}/{processed.name}"
                        public_url = upload_large_file_to_s3(processed, S3_BUCKET, s3_key)
                        if public_url:
                            _log(f"✅ Uploaded: {public_url}")
                            # Remove local file if needed
                            try:
                                os.remove(processed)
                                _log(f"Removed local file: {processed}")
                            except Exception as e:
                                _log(f"Failed to remove local file: {e}")
                        else:
                            _log(f"🔥 Upload failed for {processed}")
                            continue
                    except Exception as e:
                        _log(f"🔥 Upload failed: {e}")
                        continue
                    # After upload, update booking status to 'video_uploaded'
                    try:
                        booking_id = meta.get("booking_id")
                        if booking_id:
                            supabase.table("bookings").update({"status": "video_uploaded"}).eq("id", booking_id).execute()
                            _log(f"Booking {booking_id} status set to 'video_uploaded'")
                    except Exception as e:
                        _log(f"Failed to update booking status to video_uploaded: {e}")
                    # Insert video metadata
                    try:
                        supabase.table("videos").insert({
                            "user_id": user_id,
                            "video_url": public_url,
                            "date": date_folder.name,
                            "recording_id": video_file.stem,
                            "duration_seconds": duration
                        }).execute()
                    except Exception as e:
                        _log(f"Failed to insert video metadata: {e}")
                    # Delete booking after upload
                    booking_id = meta.get("booking_id")
                    if booking_id:
                        try:
                            supabase.table("bookings").delete().eq("id", booking_id).execute()
                            _log(f"Deleted booking {booking_id} after upload")
                        except Exception as e:
                            _log(f"Failed to delete booking {booking_id}: {e}")
                    done_file.touch()
                except Exception as e:
                    _log(f"🔥 Error: {e}")
                finally:
                    if lock_file.exists():
                        lock_file.unlink()
        time.sleep(15)


if __name__ == "__main__":
    main()
