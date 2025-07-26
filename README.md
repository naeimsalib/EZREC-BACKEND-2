# EZREC Backend

**Automated dual-camera recording system for Raspberry Pi**

## 🚀 Quick Start

### **Single Command Deployment**

```bash
# Clone the repository
git clone https://github.com/naeimsalib/EZREC-BACKEND-2.git
cd EZREC-BACKEND-2

# Run the comprehensive deployment script
chmod +x deployment.sh
sudo ./deployment.sh
```

### **Post-Deployment Setup**

1. **Configure Environment Variables**
   ```bash
   sudo nano /opt/ezrec-backend/.env
   ```
   Fill in your actual credentials (Supabase, AWS S3, etc.)

2. **Create a Test Booking**
   ```bash
   echo '[
     {
       "id": "test-001",
       "start_time": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
       "end_time": "'$(date -u -d "+2 minutes" +"%Y-%m-%dT%H:%M:%SZ")'",
       "status": "scheduled",
       "user_id": "your-user-id",
       "camera_id": "your-camera-id"
     }
   ]' | sudo tee /opt/ezrec-backend/api/local_data/bookings.json
   ```

3. **Monitor the System**
   ```bash
   # Watch recording logs
   sudo journalctl -u dual_recorder.service -f
   
   # Check system status
   sudo python3 test_system_readiness.py
   ```

## 📁 Project Structure

```
EZREC-BACKEND-2/
├── deployment.sh              # 🎯 Single comprehensive deployment script
├── env.example               # Environment variables template
├── test_system_readiness.py  # System health check
├── backend/                  # Core recording services
│   ├── dual_recorder.py      # Main dual-camera recorder
│   ├── video_worker.py       # Video processing & upload
│   ├── enhanced_merge.py     # Robust video merging
│   ├── booking_manager.py    # Booking management
│   ├── camera_health_check.py # Camera validation
│   └── cleanup_old_data.py   # Data cleanup
├── api/                      # FastAPI backend
│   ├── api_server.py         # Main API server
│   └── templates/            # HTML templates
└── systemd/                  # Service definitions
    ├── dual_recorder.service
    └── video_worker.service
```

## 🔧 What the Deployment Script Does

The `deployment.sh` script handles **everything** automatically:

1. **🛑 Stops existing services** and cleans up
2. **📁 Copies project files** to `/opt/ezrec-backend`
3. **🔧 Installs dependencies** (FFmpeg, v4l2-utils, picamera2, Python packages)
4. **📁 Creates required directories** (logs, recordings, processed, etc.)
5. **🐍 Sets up Python virtual environment** with all dependencies
6. **🔐 Fixes permissions** and ownership
7. **⚙️ Creates systemd services** with proper restart policies
8. **⏰ Sets up cron jobs** for maintenance
9. **🚀 Enables and starts all services**
10. **🧪 Tests basic functionality** (FFmpeg, cameras, Python imports)
11. **🌐 Tests API endpoint**
12. **🔍 Runs system readiness test**

## 🎬 Recording Lifecycle & Status Markers

Each recording passes through the following lifecycle, tracked by marker files:

| Marker File         | Meaning                                 |
|--------------------|-----------------------------------------|
| `.lock`            | Recording or processing in progress      |
| `.done`            | Recording completed, ready for processing|
| `.merged`          | Dual camera merge successful             |
| `.merge_error`     | Merge failed after all retries           |
| `.completed`       | Video processed and uploaded             |
| `.error`           | Fatal error (corrupt, missing, etc)      |

**Lifecycle Example:**
1. `.lock` created when recording starts
2. `.done` created when recording finishes
3. `.merged` created after successful merge (dual camera)
4. `.completed` created after upload
5. `.merge_error` or `.error` created if a step fails

## 🚀 Dual Camera Merging (New Standard)

**As of July 2025, all dual camera merging is handled by [`backend/enhanced_merge.py`](backend/enhanced_merge.py).**

- Uses robust retry logic (up to 3 attempts)
- Validates input and output files
- Logs all merge attempts and errors
- Creates marker files for downstream processing:
  - `.merged` after successful merge
  - `.merge_error` if all retries fail
- Only triggers upload if merge is successful

**Do not use legacy FFmpeg merge logic. Always use `merge_videos_with_retry(...)` from `enhanced_merge.py`.**

## 🔧 Useful Commands

```bash
# Check service status
sudo systemctl status dual_recorder.service
sudo systemctl status video_worker.service
sudo systemctl status ezrec-api.service

# View logs
sudo journalctl -u dual_recorder.service -f
sudo journalctl -u video_worker.service -f

# Restart services
sudo systemctl restart dual_recorder.service
sudo systemctl restart video_worker.service

# Test system health
sudo python3 test_system_readiness.py

# Check API health
curl http://localhost:8000/health

# Manual cleanup
sudo python3 backend/cleanup_old_data.py --dry-run
```

## 📊 Monitoring & Health Checks

### **API Endpoints**

- `GET /health` - Comprehensive system health check
- `GET /status` - System status and metrics
- `GET /recording-logs` - Recent recording logs
- `GET /booking-stats` - Booking statistics

### **System Health Check**

```bash
sudo python3 test_system_readiness.py
```

Tests:
- ✅ Environment variables
- ✅ Required directories
- ✅ FFmpeg, FFprobe, v4l2-ctl
- ✅ Camera devices
- ✅ API health
- ✅ System services

## 🧹 Maintenance

### **Automatic Cleanup**

Cron jobs handle maintenance automatically:
- **Daily cleanup** at 3 AM (recordings, logs, temp files)
- **Weekly health checks** on Sundays at 2 AM
- **Service monitoring** every 30 minutes

### **Manual Cleanup**

```bash
# Dry run to see what would be cleaned
sudo python3 backend/cleanup_old_data.py --dry-run

# Actual cleanup
sudo python3 backend/cleanup_old_data.py
```

## 🔧 Troubleshooting

### **Common Issues**

1. **Camera not detected**
   ```bash
   v4l2-ctl --list-devices
   sudo python3 backend/camera_health_check.py --verbose
   ```

2. **Service not starting**
   ```bash
   sudo systemctl status dual_recorder.service
   sudo journalctl -u dual_recorder.service -n 50
   ```

3. **Permission issues**
   ```bash
   sudo chown -R root:root /opt/ezrec-backend
   sudo chmod -R 755 /opt/ezrec-backend
   ```

### **Log Files**

- `/opt/ezrec-backend/logs/dual_recorder.log`
- `/opt/ezrec-backend/logs/video_worker.log`
- `/opt/ezrec-backend/logs/camera_health.log`

## 📋 Environment Variables

Create `/opt/ezrec-backend/.env` with:

```bash
# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_REGION=us-east-1
AWS_S3_BUCKET=your_s3_bucket_name_here
AWS_USER_MEDIA_BUCKET=your_user_media_bucket_here

# Camera Configuration
CAMERA_0_SERIAL=88000
CAMERA_1_SERIAL=80000
DUAL_CAMERA_MODE=true

# User Configuration
USER_ID=your_user_id_here
CAMERA_ID=your_camera_id_here

# Email Configuration (for share links)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password_here
EMAIL_USE_TLS=True
EMAIL_FROM=your_email@gmail.com

# Share Configuration
SHARE_BASE_URL=https://yourdomain.com

# Timezone
TIMEZONE_NAME=UTC

# Recording Configuration
RECORDING_QUALITY=high
MERGE_METHOD=side_by_side
```

## 🎯 Key Features

- ✅ **Single command deployment** - Everything handled by `deployment.sh`
- ✅ **Robust dual-camera recording** with automatic merging
- ✅ **Enhanced error handling** with retry logic
- ✅ **Comprehensive health monitoring** and status tracking
- ✅ **Automatic cleanup** and maintenance
- ✅ **FastAPI backend** with monitoring endpoints
- ✅ **Systemd services** with automatic restart
- ✅ **Cron jobs** for maintenance tasks

## 📄 License

This project is licensed under the MIT License.

---

**Made with ❤️ for automated video recording on Raspberry Pi**
