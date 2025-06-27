# EZREC Backend - Service Algorithms & Detailed Workflow

This document provides a detailed explanation of the algorithms, logic, and workflows for each microservice in the EZREC Backend system.

---

## 1. Booking Sync Service (`booking_sync.py`)

### **Purpose**
- Fetches bookings from Supabase every 3 seconds.
- Updates `bookings_cache.json` with new, edited, or deleted bookings.

### **Main Algorithm**
- On startup, loads the last local cache (if any).
- Every 3 seconds:
  - Fetches all bookings for the current user/camera from Supabase.
  - Compares with the local cache.
  - If there are changes (new, edited, or deleted bookings), updates `bookings_cache.json`.

### **Key Configuration**
- `BOOKING_FETCH_INTERVAL` (default: 3 seconds)
- `BOOKING_CACHE_FILE` (default: `/opt/ezrec-backend/bookings_cache.json`)

### **Error Handling**
- Logs all fetch and file errors.
- Continues running even if a fetch or save fails.

### **Interactions**
- Writes to `bookings_cache.json` (read by `recorder.py`).
- Reads from Supabase `bookings` table.

---

## 2. Main Recording Service (`recorder.py`)

### **Purpose**
- Reads bookings from `bookings_cache.json`.
- Starts/stops video recordings at scheduled times.
- Saves raw recordings to `/opt/ezrec-backend/raw_recordings/`.
- Sets booking status to `'completed'` in Supabase after recording finishes.

### **Main Algorithm**
- Every 3 seconds:
  - Loads bookings from `bookings_cache.json`.
  - Checks if there is an active booking for the current time.
  - If a new booking is active, starts a new recording session.
  - If no booking is active, stops any ongoing recording.
- Each recording is saved as a raw `.mp4` file with a unique name.
- When a recording finishes, updates the booking's status in Supabase to `'completed'`.

### **Key Configuration**
- `BOOKING_CHECK_INTERVAL` (default: 3 seconds)
- `RAW_RECORDINGS_DIR` (default: `/opt/ezrec-backend/raw_recordings/`)

### **Error Handling**
- Logs all camera and file errors.
- Continues running even if a recording fails.

### **Interactions**
- Reads from `bookings_cache.json` (written by `booking_sync.py`).
- Writes raw video files to `raw_recordings/` (read by `video_worker.py`).
- Updates the `status` field in the `bookings` table to `'completed'` after recording.

---

## 3. Video Processing & Upload Service (`video_worker.py`)

### **Purpose**
- Watches `raw_recordings/` for new files.
- Fetches the latest intro video and logo from Supabase (`user_settings`).
- Manages local cache for intro/logo (downloads new, deletes old if removed).
- Processes video (concatenates intro, overlays logo).
- Uploads to Supabase Storage, updates the DB, retries failed uploads.
- Updates booking status to `'video_processed'` after processing and `'video_uploaded'` after upload.

### **Main Algorithm**
- Every 5 seconds:
  - Scans `raw_recordings/` for new `.mp4` files.
  - For each file:
    - Fetches latest intro video and logo paths from Supabase.
    - Downloads/updates/deletes local intro/logo as needed.
    - Processes the video:
      - Concatenates intro (if present) before the main recording.
      - Overlays logo (if present) on the main recording only.
    - After processing, updates the booking's status in Supabase to `'video_processed'`.
    - Uploads the processed video to Supabase Storage.
    - Updates the `videos` table in Supabase.
    - After successful upload, updates the booking's status in Supabase to `'video_uploaded'`.
    - Deletes local files after successful upload.
    - If upload fails, logs error and retries on next run.

### **Key Configuration**
- `VIDEO_WORKER_CHECK_INTERVAL` (default: 5 seconds)
- `MEDIA_CACHE_DIR` (default: `/opt/ezrec-backend/media_cache/`)
- `PROCESSED_RECORDINGS_DIR` (default: `/opt/ezrec-backend/processed_recordings/`)

### **Error Handling**
- Logs all processing, upload, and DB errors.
- Skips failed files and retries later.
- Cleans up temp files after processing.

### **Interactions**
- Reads from `raw_recordings/` (written by `recorder.py`).
- Reads/writes intro/logo in `media_cache/` (from Supabase `user_settings`).
- Uploads to Supabase Storage and updates the `videos` table.
- Updates the `status` field in the `bookings` table to `'video_processed'` after processing and `'video_uploaded'` after upload.

---

### **Booking Status Values in Supabase**
- `confirmed`: Booking is upcoming or active
- `completed`: Recording finished, not yet processed
- `video_processed`: Video processed, not yet uploaded
- `video_uploaded`: Video uploaded and available

---

## 4. System Status Service (`system_status.py`)

### **Purpose**
- Collects system info (CPU, memory, disk, temp, etc.) every 1 second.
- Updates the `system_status` table in Supabase.

### **Main Algorithm**
- Every 1 second:
  - Collects CPU, memory, disk, temperature, and other system metrics.
  - Updates or inserts a row in the `system_status` table for the current camera/user.

### **Key Configuration**
- `SYSTEM_STATUS_INTERVAL` (default: 1 second)

### **Error Handling**
- Logs all system info and DB errors.
- Continues running even if an update fails.

### **Interactions**
- Writes to the `system_status` table in Supabase.

---

## **General Notes**
- All services are designed to run independently and communicate via local files and Supabase.
- All configuration is via environment variables or `.env`.
- All logs are written to `/opt/ezrec-backend/logs/` for troubleshooting.
- For more details, see the code comments and docstrings in each script. 