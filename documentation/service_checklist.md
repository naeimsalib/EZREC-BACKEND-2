# EZREC Backend Service Checklist

This checklist is based strictly on the code logic of each service. Use it to verify, audit, or extend your deployment.

---

## 1. booking_sync.py
- [ ] Loads environment variables for Supabase URL, key, user ID, camera ID, and cache file path
- [ ] Sets up logging to `/opt/ezrec-backend/logs/booking_sync.log`
- [ ] On each interval:
  - [ ] Calls Supabase `.table('bookings').select('*').eq('user_id', USER_ID).eq('camera_id', CAMERA_ID).execute()`
  - [ ] If successful, writes the bookings to `bookings_cache.json`
  - [ ] If failed, logs the error and continues
- [ ] Runs forever, sleeping for the configured interval between fetches

---

## 2. recorder.py
- [ ] Loads environment variables for Supabase, user/camera ID, cache file, and raw recordings directory
- [ ] Sets up logging to `/opt/ezrec-backend/logs/recorder.log`
- [ ] Ensures the raw recordings directory exists
- [ ] On each interval:
  - [ ] Loads bookings from `bookings_cache.json`
  - [ ] Checks if the current time matches any booking's window
  - [ ] If a new booking is active and not already recording:
    - [ ] Starts a new recording using `picamera2`
    - [ ] Saves the video as a raw `.mp4` file
  - [ ] If no booking is active and currently recording:
    - [ ] Stops the recording
    - [ ] Updates the booking's status in Supabase to `"completed"`
- [ ] Handles camera errors and logs them
- [ ] Runs forever, sleeping for the configured interval

---

## 3. video_worker.py
- [ ] Loads environment variables for Supabase, user ID, directories, and intervals
- [ ] Sets up logging to `/opt/ezrec-backend/logs/video_worker.log`
- [ ] Ensures processed recordings and media cache directories exist
- [ ] On each interval:
  - [ ] Scans for new `.mp4` files in the raw recordings directory
  - [ ] For each file:
    - [ ] Extracts `booking_id` from the filename
    - [ ] Fetches intro video and logo paths from Supabase
    - [ ] Downloads intro/logo if needed
    - [ ] Processes the video with FFmpeg (concatenate intro, overlay logo)
    - [ ] After processing, updates booking status to `"video_processed"`
    - [ ] Uploads the processed video to Supabase Storage
    - [ ] After upload, updates booking status to `"video_uploaded"`
    - [ ] Inserts video metadata into the `videos` table
    - [ ] Deletes local files after successful upload
    - [ ] If upload fails, logs the error and retries on next run
- [ ] Handles all errors robustly and logs them
- [ ] Runs forever, sleeping for the configured interval

---

## 4. system_status.py
- [ ] Loads environment variables for Supabase, user/camera ID, and interval
- [ ] Sets up logging to `/opt/ezrec-backend/logs/system_status.log`
- [ ] On each interval:
  - [ ] Collects CPU usage, memory usage, disk usage, temperature, and other metrics using `psutil` and system files
  - [ ] Updates or inserts a row in the `system_status` table for the current camera/user
  - [ ] Handles errors and logs them
- [ ] Runs forever, sleeping for the configured interval

---

## 5. log_collector.py
- [ ] Loads environment variables for Supabase, camera ID, logs directory, upload interval, and bucket name
- [ ] Sets up logging to `/opt/ezrec-backend/logs/log_collector.log`
- [ ] On each interval:
  - [ ] Collects all `.log` files and systemd journal entries for all services
  - [ ] Compresses them into a zip archive named `<timestamp>_logs.zip`
  - [ ] Uploads the archive to Supabase Storage under `/logs/<camera_id>/`
  - [ ] Deletes the local archive after upload
  - [ ] Handles errors and logs them
- [ ] Runs forever, sleeping for the configured interval

---

## Shared/All Services
- [ ] Validate `.env` on boot, log if keys are missing
- [ ] Verify that booking IDs and file names are safe (no injection or path traversal)
- [ ] Prevent parallel recorders (disable `recorder.py` if using `ezrec_backend.py`)
- [ ] Add `.lock` or `.inprogress` files during processing to prevent double execution
- [ ] Handle stale `.mp4` files in `raw_recordings/` that failed in a previous crash
- [ ] Add `FFmpeg` and `picamera2` version checks on startup
- [ ] Log full Supabase response on error if `.data` is `None`

---

**All services:**
- [ ] Use environment variables for configuration
- [ ] Log to both file and stdout
- [ ] Handle errors robustly and continue running
- [ ] Are designed to run as systemd services with auto-restart 