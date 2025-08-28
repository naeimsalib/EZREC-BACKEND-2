# EZREC System Testing Guide
*Complete Testing Documentation for EZREC Dual-Camera Recording System*

---

## 📋 Table of Contents
1. [Pre-Testing Checklist](#pre-testing-checklist)
2. [Service Status Verification](#service-status-verification)
3. [Camera System Testing](#camera-system-testing)
4. [Enhanced Merge System Testing](#enhanced-merge-system-testing)
5. [Full Recording Pipeline Test](#full-recording-pipeline-test)
6. [Video Processing Verification](#video-processing-verification)
7. [API and External Access Testing](#api-and-external-access-testing)
8. [System Health Monitoring](#system-health-monitoring)
9. [Troubleshooting Commands](#troubleshooting-commands)
10. [Success/Failure Indicators](#successfailure-indicators)

---

## 🔍 Pre-Testing Checklist

**Before starting any tests, ensure:**
- [ ] All services are deployed and running
- [ ] Environment variables are properly configured
- [ ] Cameras are connected and accessible
- [ ] Sufficient disk space available (>10GB free)
- [ ] Network connectivity to Supabase and S3
- [ ] Cloudflare tunnel is configured (if using external access)

---

## 🚀 Service Status Verification

### Check All Services Status
```bash
# Check if all services are running
sudo systemctl status dual_recorder.service
sudo systemctl status video_worker.service
sudo systemctl status ezrec-api.service
sudo systemctl status system_status.service

# Check for any failed services
sudo systemctl --failed

# Check service logs for errors
sudo journalctl -u dual_recorder.service -n 50 --no-pager
sudo journalctl -u video_worker.service -n 50 --no-pager
sudo journalctl -u ezrec-api.service -n 50 --no-pager
```

**Expected Result:** All services show "active (running)" status

---

## 📷 Camera System Testing

### Verify Camera Hardware
```bash
# Check camera devices
ls -la /dev/video*

# Check camera permissions
ls -la /dev/video* | grep video

# Test camera access
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --list-formats-ext
v4l2-ctl -d /dev/video1 --list-formats-ext
```

**Expected Result:** Two video devices (/dev/video0, /dev/video1) accessible with video group permissions

### Test Camera Initialization
```bash
# Navigate to backend directory
cd /opt/ezrec-backend/backend

# Activate virtual environment
source venv/bin/activate

# Test camera initialization
python3 -c "
import picamera2
print('✅ picamera2 import successful')
camera = picamera2.Picamera2()
camera.configure(camera.create_preview_configuration())
camera.start()
print('✅ Camera started successfully')
camera.stop()
print('✅ Camera stopped successfully')
"
```

**Expected Result:** No import errors, camera starts and stops cleanly

---

## 🔧 Enhanced Merge System Testing

### Test Enhanced Merge (Dry Run)
```bash
# Navigate to backend directory
cd /opt/ezrec-backend/backend

# Activate virtual environment
source venv/bin/activate

# Test enhanced merge with dry run
python3 enhanced_merge.py \
  /opt/ezrec-backend/recordings/2025-08-05/224800-224900_65aa2e2a-e463-424d-b88f-0724bb0bea3a_d217e751-dfa5-5276-abbb-da5ad6c2626a_left.mp4 \
  /opt/ezrec-backend/recordings/2025-08-05/224800-224900_65aa2e2a-e463-424d-b88f-0724bb0bea3a_d217e751-dfa5-5276-abbb-da5ad6c2626a_right.mp4 \
  /tmp/test_merge.mp4 \
  --method side_by_side \
  --dry-run
```

**Expected Result:** FFmpeg command displays without errors, no `TypeError: can only join an iterable`

### Test Enhanced Merge (Actual Execution)
```bash
# Test actual merge with existing files
python3 enhanced_merge.py \
  /opt/ezrec-backend/recordings/2025-08-05/224800-224900_65aa2e2a-e463-424d-b88f-0724bb0bea3a_d217e751-dfa5-5276-abbb-da5ad6c2626a_left.mp4 \
  /opt/ezrec-backend/recordings/2025-08-05/224800-224900_65aa2e2a-e463-424d-b88f-0724bb0bea3a_d217e751-dfa5-5276-abbb-da5ad6c2626a_right.mp4 \
  /tmp/test_merge_output.mp4 \
  --method side_by_side \
  --retries 2 \
  --timeout 300
```

**Expected Result:** Merge completes in 1-2 minutes, output file created successfully

### Verify Merge Output
```bash
# Check if merge output was created
ls -la /tmp/test_merge_output.mp4

# Validate the merged video
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,duration -of json /tmp/test_merge_output.mp4

# Check file size
du -h /tmp/test_merge_output.mp4
```

**Expected Result:** Valid MP4 file with dimensions 3740x1080 (for side-by-side), reasonable file size

---

## 🎬 Full Recording Pipeline Test

### Monitor Complete Pipeline
```bash
# In separate terminals, monitor each service:

# Terminal 1: Monitor dual_recorder
sudo journalctl -u dual_recorder.service -f

# Terminal 2: Monitor video_worker
sudo journalctl -u video_worker.service -f

# Terminal 3: Monitor system status
sudo journalctl -u system_status.service -f

# Terminal 4: Monitor API server
sudo journalctl -u ezrec-api.service -f
```

### Check File Generation
```bash
# Monitor recordings directory for new files
watch -n 2 'ls -la /opt/ezrec-backend/recordings/$(date +%Y-%m-%d)/'

# Check for merge files
find /opt/ezrec-backend/recordings -name "*merged.mp4" -type f -exec ls -la {} \;

# Check for .done markers
find /opt/ezrec-backend/recordings -name "*.done" -type f
```

**Expected Result:** New recording files appear, merge files created, .done markers present

---

## 🎥 Video Processing Verification

### Monitor Video Worker Processing
```bash
# Check if video_worker is processing files
ps aux | grep video_worker

# Check video_worker logs for processing activity
sudo journalctl -u video_worker.service -n 100 | grep -E "(Processing|Uploading|Completed)"

# Check for processed videos
find /opt/ezrec-backend/recordings -name "*concat_*" -type f
```

**Expected Result:** Logo overlay completes, intro video concatenation works, final video created

### Test Video Upload (if configured)
```bash
# Check S3 upload status
aws s3 ls s3://ezrec-user-media/ --recursive | grep $(date +%Y-%m-%d)

# Check for upload events
ls -la /opt/ezrec-backend/events/
```

**Expected Result:** Videos uploaded to S3, upload events recorded

---

## 🌐 API and External Access Testing

### Test API Server Functionality
```bash
# Test API server health endpoint
curl -v http://localhost:8000/test-alive

# Test API server on port 9000 (fallback)
curl -v http://localhost:9000/test-alive

# Check if API server is listening on correct ports
sudo lsof -i :8000
sudo lsof -i :9000
```

**Expected Result:** API responds with success, ports 8000/9000 are listening

### Test Share Link Creation
```bash
# Test share link creation (if you have a video ID)
curl -X POST "http://localhost:8000/share" \
  -H "Content-Type: application/json" \
  -d '{"video_id": "test-video-id", "email": "test@example.com"}'

# Check API response
curl -v http://localhost:8000/status
```

**Expected Result:** Share link created successfully, no authentication errors

### Test External Access
```bash
# Test from another device on the network
curl -v http://192.168.1.32:8000/test-alive

# Test Cloudflare tunnel
curl -v --max-time 10 https://api.ezrec.org/status
```

**Expected Result:** External access works, Cloudflare tunnel responds

---

## 💻 System Health Monitoring

### Check System Resources
```bash
# Check disk usage
df -h

# Check memory usage
free -h

# Check CPU usage
htop

# Check temperature (Raspberry Pi)
vcgencmd measure_temp
```

**Expected Result:** Disk usage <90%, memory usage reasonable, temperature <80°C

### Check Log Files
```bash
# Check log file sizes
ls -lah /opt/ezrec-backend/logs/

# Check for error patterns
grep -i error /opt/ezrec-backend/logs/*.log | tail -20

# Check for warning patterns
grep -i warning /opt/ezrec-backend/logs/*.log | tail -20
```

**Expected Result:** Log files manageable size, minimal errors/warnings

---

## 🛠️ Troubleshooting Commands

### Service Diagnostics
```bash
# Check service dependencies
sudo systemctl list-dependencies dual_recorder.service

# Check for port conflicts
sudo lsof -i :8000
sudo lsof -i :9000

# Check for zombie processes
ps aux | grep -E "(python|ffmpeg)" | grep -v grep

# Check systemd service logs
sudo journalctl -u dual_recorder.service --since "1 hour ago" --no-pager
```

### File System Issues
```bash
# Check for file permission issues
ls -la /opt/ezrec-backend/recordings/
ls -la /opt/ezrec-backend/logs/

# Check disk space
df -h /opt/ezrec-backend/

# Check for corrupted files
find /opt/ezrec-backend/recordings -name "*.mp4" -exec ffprobe -v error {} \; 2>&1 | grep -i error
```

### Network and External Services
```bash
# Test Supabase connectivity
curl -v https://iszmsaayxpdrovealrrp.supabase.co/rest/v1/

# Test S3 connectivity
aws s3 ls s3://ezrec-user-media/ --max-items 1

# Check Cloudflare tunnel status
cloudflared tunnel list
```

---

## ✅ Success Indicators

### Camera System
- [ ] Both cameras initialize without errors
- [ ] Recording starts and stops cleanly
- [ ] No "camera closed unexpectedly" errors
- [ ] MP4 files generated with correct sizes

### Enhanced Merge
- [ ] FFmpeg command generates correctly
- [ ] No `TypeError: can only join an iterable`
- [ ] Merge completes in reasonable time (1-2 minutes)
- [ ] Output file is valid MP4 with correct dimensions

### Video Processing
- [ ] Logo overlay completes successfully
- [ ] Intro video concatenation works
- [ ] Final video uploads to S3
- [ ] No processing timeouts or crashes

### System Services
- [ ] All services show "active (running)" status
- [ ] No service failures or restarts
- [ ] Clean logs without critical errors
- [ ] Ports 8000/9000 accessible

---

## ❌ Failure Indicators

### Camera Issues
- [ ] "Camera closed unexpectedly" errors
- [ ] Permission denied errors on /dev/video*
- [ ] picamera2 import failures
- [ ] No video files generated

### Merge Issues
- [ ] `TypeError: can only join an iterable`
- [ ] FFmpeg syntax errors
- [ ] Merge timeouts or crashes
- [ ] Invalid output files

### Service Issues
- [ ] Services showing "failed" status
- [ ] Port conflicts (address already in use)
- [ ] Supabase authentication errors
- [ ] Service crashes or restarts

### System Issues
- [ ] High disk usage (>90%)
- [ ] High memory usage (>80%)
- [ ] High temperature (>80°C)
- [ ] Network connectivity issues

---

## 📝 Testing Notes

### Recording Session Test
- **Duration:** 1-2 minutes minimum
- **Expected Output:** 3740x1080 merged video
- **Processing Time:** 2-5 minutes total
- **File Sizes:** Individual: 15-45MB, Merged: 20-60MB

### Performance Benchmarks
- **Camera Initialization:** <5 seconds
- **Recording Start:** <2 seconds
- **Merge Processing:** 1-2 minutes per minute of video
- **Logo Overlay:** 30-60 seconds
- **Total Pipeline:** 3-8 minutes for 1-minute recording

### Common Issues to Watch
1. **Camera Permission Errors:** Check video group membership
2. **Merge Failures:** Verify input file validity
3. **Service Crashes:** Check logs for root cause
4. **Port Conflicts:** Ensure no other services using 8000/9000
5. **Disk Space:** Monitor available space during recording

---

## 🔄 Regular Maintenance Testing

### Daily Checks
- [ ] Service status verification
- [ ] Log file size monitoring
- [ ] Disk space verification

### Weekly Checks
- [ ] Full recording pipeline test
- [ ] Enhanced merge system test
- [ ] API functionality test
- [ ] External access verification

### Monthly Checks
- [ ] Complete system health assessment
- [ ] Performance benchmark testing
- [ ] Backup verification
- [ ] Security updates check

---

*This testing guide covers all critical aspects of the EZREC system. Use it systematically to ensure optimal performance and identify issues early.* 