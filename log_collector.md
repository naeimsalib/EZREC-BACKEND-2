# EZREC Log Collector Service

## Purpose
- Continuously collects logs from all EZREC Backend services and systemd journal.
- Compresses and uploads logs to Supabase Storage ('logs' bucket) for later review.
- Organizes logs by physical camera ID for easy troubleshooting and audit.

## How It Works
- Every N minutes (default: 15), collects all `.log` files from `/opt/ezrec-backend/logs/` and recent systemd journal entries for each service.
- Compresses them into a single zip archive named `<YYYYMMDD_HHMMSS>_logs.zip`.
- Uploads the archive to the Supabase Storage bucket `logs` under a folder named after the camera ID: `/logs/<camera_id>/<timestamp>_logs.zip`.
- Deletes the local archive after successful upload.
- Runs as a 24/7 systemd service on the Pi.

## Configuration
- All settings are via environment variables or `.env`:
  - `LOGS_DIR`: Directory containing service logs (default: `/opt/ezrec-backend/logs`)
  - `LOG_UPLOAD_INTERVAL`: Upload interval in seconds (default: 900 = 15 min)
  - `LOG_BUCKET`: Supabase Storage bucket for logs (default: `logs`)
  - `CAMERA_ID`: Used to organize logs in storage
  - `SUPABASE_URL`, `SUPABASE_KEY`: Supabase credentials

## Deployment
1. Place `log_collector.py` in `/opt/ezrec-backend/`.
2. Place `log_collector.service` in your systemd unit directory (or use deployment script).
3. Enable and start the service:
   ```bash
   sudo systemctl enable log_collector
   sudo systemctl start log_collector
   ```
4. Check status and logs:
   ```bash
   sudo systemctl status log_collector
   sudo journalctl -u log_collector -f
   ```

## Reviewing Logs
- All logs are uploaded to Supabase Storage in the `logs` bucket, organized by camera ID.
- To review logs for a specific time or camera, download the relevant zip archive from Supabase Storage.
- You can request a log review by providing the archive name or time window.

## Example Storage Layout
```
logs/
  <camera_id>/
    20240619_153000_logs.zip
    20240619_154500_logs.zip
    ...
```

## Troubleshooting
- The log collector logs its own actions to `/opt/ezrec-backend/logs/log_collector.log` and the systemd journal.
- If uploads fail, check network connectivity and Supabase credentials.
- Ensure the `logs` bucket exists in Supabase Storage (the service will create it if missing).

---

**This service ensures you always have a full audit trail and can request log reviews for any period or camera.** 