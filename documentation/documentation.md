# EZREC Backend - Service Algorithms & Detailed Workflow

This document provides a detailed explanation of the algorithms, logic, and workflows for each microservice in the EZREC Backend system.

---

## 1. Main Recording Service (`recorder.py`)

### **Purpose**

- Reads bookings from the API-managed cache file (`bookings.json`).
- Starts/stops video recordings at scheduled times.
- Saves raw recordings to `/opt/ezrec-backend/raw_recordings/`.
- Sets booking status to `'completed'` in Supabase after recording finishes.

### **Main Algorithm**

- Every 3 seconds:
  - Loads bookings from the API-managed cache file.
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

- Reads from the API-managed bookings cache file.
- Writes raw video files to `raw_recordings/` (read by `video_worker.py`).
- Updates the `status` field in the `bookings` table to `'completed'` after recording.

---

## 2. Video Processing & Upload Service (`video_worker.py`)

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
- Uploads processed videos to Supabase Storage.
- Updates the `videos` and `bookings` tables in Supabase.

---

## 3. System Status Service (`system_status.py`)

### **Purpose**

- Collects and uploads system health metrics to Supabase.

### **Main Algorithm**

- Periodically collects CPU, memory, disk, and other system stats.
- Uploads metrics to Supabase for monitoring and alerting.

### **Key Configuration**

- `SYSTEM_STATUS_INTERVAL` (default: 60 seconds)

### **Error Handling**

- Logs all errors.
- Continues running even if a metric upload fails.

### **Interactions**

- Updates the `system_status` table in Supabase.

---

## 4. API Server (`api_server.py`)

### **Purpose**

- Provides a FastAPI backend for managing bookings, system status, and media notifications.
- Manages the bookings cache file used by the recorder.

### **Main Algorithm**

- Exposes endpoints for bookings, system status, and media notifications.
- Handles POST/GET requests for bookings and updates the local cache file accordingly.
- Handles notifications for new/updated media (logos, intros, etc.).

### **Key Configuration**

- `API_PORT` (default: 8000)

### **Error Handling**

- Logs all API errors.
- Returns appropriate HTTP error codes.

### **Interactions**

- Reads/writes the bookings cache file.
- Communicates with Supabase for user and booking data.

---

**Note:** The Booking Sync Service (`booking_sync.py`) is no longer used. Bookings are now managed directly via the API/backend, and the cache is updated by the API server.

### **Booking Status Values in Supabase**

- `confirmed`: Booking is upcoming or active
- `completed`: Recording finished, not yet processed
- `video_processed`: Video processed, not yet uploaded
- `video_uploaded`: Video uploaded and available
