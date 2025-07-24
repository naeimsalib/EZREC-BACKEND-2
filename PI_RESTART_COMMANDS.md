# EZREC Pi Restart and Log Analysis Commands

## Summary of Changes Made

✅ **Removed Live View Functionality:**
- Deleted `camera_streamer.py` and its service file
- Removed `/live-preview` endpoint from API server
- Updated `recorder.py` to use direct picamera2 recording
- Removed camera_streamer references from deployment script
- Updated test_camera.py to remove camera_streamer dependencies

✅ **Fixed Recorder Issues:**
- Fixed indentation problems in `stop()` method
- Updated to use direct picamera2 recording instead of camera_streamer
- Added proper error handling and camera cleanup
- Fixed metadata generation

## Commands to Run on Your Raspberry Pi

### 1. Copy Updated Files to Pi

First, copy the updated files to your Pi. You can either:
- Use `scp` to copy individual files
- Use `rsync` to sync the entire project
- Or manually copy the files

```bash
# Option 1: Copy specific files
scp backend/recorder.py pi@your-pi-ip:/opt/ezrec-backend/backend/
scp api/api_server.py pi@your-pi-ip:/opt/ezrec-backend/api/
scp backend/test_camera.py pi@your-pi-ip:/opt/ezrec-backend/backend/
scp restart_services.sh pi@your-pi-ip:/opt/ezrec-backend/
scp analyze_logs.sh pi@your-pi-ip:/opt/ezrec-backend/

# Option 2: Sync entire project (recommended)
rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' ./ pi@your-pi-ip:/opt/ezrec-backend/
```

### 2. SSH into Your Pi

```bash
ssh pi@your-pi-ip
```

### 3. Stop All Services and Clean Up

```bash
# Stop all EZREC services
sudo systemctl stop recorder.service
sudo systemctl stop video_worker.service
sudo systemctl stop system_status.service
sudo systemctl stop log_collector.service
sudo systemctl stop health_api.service

# Kill any camera processes
sudo fuser -k /dev/video0 2>/dev/null || true
sleep 2

# Remove old camera_streamer service if it exists
sudo systemctl disable camera_streamer.service 2>/dev/null || true
sudo rm -f /etc/systemd/system/camera_streamer.service
```

### 4. Reload Systemd and Restart Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Start services in order
sudo systemctl start recorder.service
sleep 3
sudo systemctl start video_worker.service
sleep 3
sudo systemctl start system_status.service
sleep 3
sudo systemctl start log_collector.service
sleep 3
sudo systemctl start health_api.service

# Enable services for auto-start
sudo systemctl enable recorder.service
sudo systemctl enable video_worker.service
sudo systemctl enable system_status.service
sudo systemctl enable log_collector.service
sudo systemctl enable health_api.service
```

### 5. Check Service Status

```bash
# Check all service statuses
sudo systemctl status recorder.service
sudo systemctl status video_worker.service
sudo systemctl status system_status.service
sudo systemctl status log_collector.service
sudo systemctl status health_api.service

# Or check all at once
sudo systemctl list-units --type=service | grep -E "(recorder|video_worker|system_status|log_collector|health_api)"
```

### 6. Run the Restart Script (Alternative)

If you copied the restart script, you can use it instead:

```bash
cd /opt/ezrec-backend
sudo chmod +x restart_services.sh
sudo ./restart_services.sh
```

### 7. Analyze Logs and Identify Issues

```bash
# Run the log analysis script
cd /opt/ezrec-backend
sudo chmod +x analyze_logs.sh
sudo ./analyze_logs.sh
```

### 8. Manual Log Review Commands

If you prefer to check logs manually:

```bash
# View recent logs for each service
sudo journalctl -u recorder.service -n 50 --no-pager
sudo journalctl -u video_worker.service -n 50 --no-pager
sudo journalctl -u system_status.service -n 50 --no-pager
sudo journalctl -u log_collector.service -n 50 --no-pager
sudo journalctl -u health_api.service -n 50 --no-pager

# Check for errors in the last hour
sudo journalctl --since "1 hour ago" | grep -i "error\|fail\|exception"

# Check application logs
tail -50 /opt/ezrec-backend/logs/ezrec.log
tail -50 /opt/ezrec-backend/logs/recorder.log
tail -50 /opt/ezrec-backend/logs/video_worker.log

# Check system resources
free -h
df -h
vcgencmd measure_temp

# Check camera
ls -la /dev/video*
groups pi
```

### 9. Test Camera Functionality

```bash
# Test camera directly
cd /opt/ezrec-backend/backend
sudo python3 test_camera.py
```

### 10. Monitor Services in Real-Time

```bash
# Monitor all services
sudo journalctl -f

# Monitor specific service
sudo journalctl -u recorder.service -f

# Monitor application logs
tail -f /opt/ezrec-backend/logs/ezrec.log
```

### 11. Share Logs for Analysis

After running the analysis script, you can share the logs:

```bash
# Create a compressed archive of the analysis
cd /tmp
tar -czf ezrec_logs_$(date +%Y%m%d_%H%M%S).tar.gz ezrec_log_analysis_*

# Copy to your local machine
scp ezrec_logs_*.tar.gz your-username@your-local-ip:/path/to/save/
```

## Common Issues and Solutions

### Issue: Camera not detected
```bash
# Check camera connection
ls -la /dev/video*
# Should show /dev/video0

# Check camera permissions
groups pi
# Should include 'video' group

# Add user to video group if needed
sudo usermod -a -G video pi
```

### Issue: Services not starting
```bash
# Check service logs for specific errors
sudo journalctl -u recorder.service -n 20

# Check if .env file exists and has correct values
ls -la /opt/ezrec-backend/.env
cat /opt/ezrec-backend/.env | grep -E "^(SUPABASE_URL|SUPABASE_KEY|USER_ID|CAMERA_ID)="
```

### Issue: Network connectivity problems
```bash
# Test internet connection
ping -c 3 8.8.8.8

# Test DNS resolution
nslookup google.com

# Test Supabase connectivity (replace with your URL)
ping -c 3 iszmsaayxpdrovealrrp.supabase.co
```

### Issue: Disk space problems
```bash
# Check disk usage
df -h

# Clean up old recordings if needed
sudo find /opt/ezrec-backend/recordings -name "*.mp4" -mtime +7 -delete
sudo find /opt/ezrec-backend/logs -name "*.log" -mtime +7 -delete
```

## Expected Behavior After Restart

✅ **Services should be running:**
- `recorder.service` - Handles video recording
- `video_worker.service` - Processes and uploads videos
- `system_status.service` - Monitors system health
- `log_collector.service` - Collects and uploads logs
- `health_api.service` - Provides health endpoint

✅ **No more camera_streamer:**
- The camera_streamer service should not exist
- Recording now uses direct picamera2 integration
- No more live preview functionality

✅ **Logs should show:**
- Successful service starts
- Camera initialization
- Booking detection
- Recording start/stop events

## Next Steps

1. **Run the restart commands above**
2. **Check service status** - All services should be active
3. **Run log analysis** - Use the analyze_logs.sh script
4. **Share the analysis results** - Send the comprehensive report
5. **Monitor for 24 hours** - Watch for any recurring issues

## Support

If you encounter issues:
1. Run the log analysis script
2. Share the comprehensive report
3. Note any specific error messages
4. Check if all required environment variables are set
5. Verify camera connection and permissions 