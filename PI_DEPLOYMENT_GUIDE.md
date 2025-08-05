# EZREC Raspberry Pi Deployment Guide

## 🚀 Complete Step-by-Step Setup

This guide will walk you through deploying the EZREC backend on your Raspberry Pi and testing the entire pipeline.

## 📋 Prerequisites

### Hardware Requirements
- **Raspberry Pi 4** (4GB RAM minimum, 8GB recommended)
- **2 USB cameras** (or Pi Camera modules)
- **MicroSD card** (32GB minimum, Class 10)
- **Power supply** (5V/3A minimum)
- **Ethernet cable** (for stable network)

### Software Requirements
- **Raspberry Pi OS** (Bullseye or newer)
- **Python 3.9+**
- **Git**

## 🔧 Step 1: Initial Pi Setup

### 1.1 Update System
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y git curl wget vim htop
```

### 1.2 Install Python Dependencies
```bash
# Install Python packages
sudo apt install -y python3-pip python3-venv python3-dev

# Install system dependencies for video processing
sudo apt install -y ffmpeg libavcodec-extra libavdevice-dev libavfilter-dev libavformat-dev libavutil-dev libswscale-dev libswresample-dev

# Install camera tools
sudo apt install -y v4l-utils v4l2loopback-dkms

# Install ImageMagick for logo creation
sudo apt install -y imagemagick
```

### 1.3 Configure Camera Access
```bash
# Add user to video group
sudo usermod -a -G video $USER

# Enable camera interface
sudo raspi-config nonint do_camera 0

# Reboot to apply changes
sudo reboot
```

## 📥 Step 2: Clone and Setup Repository

### 2.1 Clone Repository
```bash
# Navigate to home directory
cd ~

# Clone the repository
git clone https://github.com/naeimsalib/EZREC-BACKEND-2.git

# Navigate to project directory
cd EZREC-BACKEND-2
```

### 2.2 Run Deployment Script
```bash
# Make deployment script executable
chmod +x deployment.sh

# Run deployment script
sudo ./deployment.sh
```

### 2.3 Verify Installation
```bash
# Check if all services are installed
sudo systemctl status dual_recorder.service video_worker.service ezrec-api.service system_status.service

# Check if directories are created
ls -la /opt/ezrec-backend/
```

## ⚙️ Step 3: Configure Environment

### 3.1 Create Environment File
```bash
# Copy example environment file
sudo cp env.example /opt/ezrec-backend/.env

# Edit environment file
sudo nano /opt/ezrec-backend/.env
```

### 3.2 Configure Required Variables
Add your actual values to the `.env` file:

```bash
# Supabase Configuration (REQUIRED)
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# User Configuration (REQUIRED)
USER_ID=your_user_id
CAMERA_ID=your_camera_id

# Camera Configuration (REQUIRED)
CAMERA_0_SERIAL=your_first_camera_serial
CAMERA_1_SERIAL=your_second_camera_serial
DUAL_CAMERA_MODE=true

# AWS Configuration (REQUIRED for upload)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
AWS_S3_BUCKET=your_s3_bucket_name

# Optional: Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
EMAIL_USE_TLS=True
EMAIL_FROM=your_email@gmail.com
```

### 3.3 Set Proper Permissions
```bash
# Set ownership
sudo chown -R ezrec:ezrec /opt/ezrec-backend

# Set permissions
sudo chmod -R 755 /opt/ezrec-backend
sudo chmod 644 /opt/ezrec-backend/.env
```

## 📹 Step 4: Camera Setup and Testing

### 4.1 Detect Cameras
```bash
# List video devices
v4l2-ctl --list-devices

# Check camera capabilities
v4l2-ctl -d /dev/video0 --list-formats-ext
v4l2-ctl -d /dev/video1 --list-formats-ext
```

### 4.2 Test Camera Access
```bash
# Navigate to backend directory
cd /opt/ezrec-backend/backend

# Activate virtual environment
source venv/bin/activate

# Run camera test
python3 quick_camera_test.py
```

### 4.3 Run Comprehensive Camera Test
```bash
# Run full camera test suite
python3 camera_test_suite.py

# Check test results
cat camera_test_results.json
```

## 🧪 Step 5: System Testing

### 5.1 Run System Health Check
```bash
# Run system readiness test
python3 test_system_readiness.py

# Check system health
python3 test_system_health.py
```

### 5.2 Test Individual Services
```bash
# Test dual recorder (without cameras)
python3 dual_recorder.py --test

# Test video worker
python3 video_worker.py --test

# Test API server
cd /opt/ezrec-backend/api
source venv/bin/activate
python3 -c "import api_server; print('API server imports successfully')"
```

### 5.3 Run Smoke Test
```bash
# Navigate to backend
cd /opt/ezrec-backend/backend
source venv/bin/activate

# Run comprehensive smoke test
python3 smoke_test.py
```

## 🚀 Step 6: Start Services

### 6.1 Enable and Start Services
```bash
# Enable all services
sudo systemctl enable dual_recorder.service
sudo systemctl enable video_worker.service
sudo systemctl enable ezrec-api.service
sudo systemctl enable system_status.service
sudo systemctl enable system_status.timer

# Start services
sudo systemctl start dual_recorder.service
sudo systemctl start video_worker.service
sudo systemctl start ezrec-api.service
sudo systemctl start system_status.timer
```

### 6.2 Verify Service Status
```bash
# Check service status
sudo systemctl status dual_recorder.service video_worker.service ezrec-api.service

# Check service logs
sudo journalctl -u dual_recorder.service -f
sudo journalctl -u video_worker.service -f
sudo journalctl -u ezrec-api.service -f
```

## 🎯 Step 7: Create Test Booking

### 7.1 Create Test Booking via API
```bash
# Create test booking
curl -X POST "http://localhost:8000/bookings" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test_booking_123",
    "user_id": "test_user",
    "camera_id": "test_camera",
    "start_time": "2024-01-15T10:00:00",
    "end_time": "2024-01-15T10:02:00",
    "status": "STARTED"
  }'
```

### 7.2 Monitor Recording Process
```bash
# Watch dual recorder logs
sudo journalctl -u dual_recorder.service -f

# Check for recording files
watch -n 2 'ls -la /opt/ezrec-backend/recordings/'

# Check for processed files
watch -n 2 'ls -la /opt/ezrec-backend/processed/'
```

## 🔍 Step 8: Troubleshooting

### 8.1 Common Issues and Solutions

#### Camera Not Detected
```bash
# Check camera hardware
sudo v4l2-ctl --list-devices

# Test camera access
python3 /opt/ezrec-backend/backend/quick_camera_test.py

# Check permissions
groups $USER
```

#### Recording Failures
```bash
# Check disk space
df -h /opt/ezrec-backend

# Check dual recorder logs
sudo journalctl -u dual_recorder.service --since "10 minutes ago"

# Check file permissions
ls -la /opt/ezrec-backend/recordings/
```

#### Processing Failures
```bash
# Check video worker logs
sudo journalctl -u video_worker.service --since "10 minutes ago"

# Check FFmpeg installation
ffmpeg -version

# Check processed files
ls -la /opt/ezrec-backend/processed/
```

#### API Server Issues
```bash
# Check API server logs
sudo journalctl -u ezrec-api.service -f

# Test API endpoint
curl http://localhost:8000/status

# Check port availability
sudo netstat -tlnp | grep :8000
```

### 8.2 Service Management Commands
```bash
# Restart all services
sudo systemctl restart dual_recorder.service video_worker.service ezrec-api.service

# Stop all services
sudo systemctl stop dual_recorder.service video_worker.service ezrec-api.service

# Check service dependencies
sudo systemctl list-dependencies dual_recorder.service
```

## 📊 Step 9: Monitoring and Validation

### 9.1 Check System Status
```bash
# Run system status check
python3 /opt/ezrec-backend/backend/system_status.py

# Check API status endpoints
curl http://localhost:8000/status/cpu
curl http://localhost:8000/status/memory
curl http://localhost:8000/status/storage
curl http://localhost:8000/status/temperature
```

### 9.2 Monitor Logs
```bash
# Follow all service logs
sudo journalctl -f -u dual_recorder.service -u video_worker.service -u ezrec-api.service

# Check specific log files
tail -f /var/log/ezrec/dual_recorder.log
tail -f /var/log/ezrec/video_worker.log
```

### 9.3 Validate Pipeline
```bash
# Check recording files
ls -la /opt/ezrec-backend/recordings/

# Check processed files
ls -la /opt/ezrec-backend/processed/

# Check final files
ls -la /opt/ezrec-backend/final/

# Check events
ls -la /opt/ezrec-backend/events/
```

## 🎉 Step 10: Final Validation

### 10.1 Run Complete Test
```bash
# Run full smoke test
cd /opt/ezrec-backend/backend
source venv/bin/activate
python3 smoke_test.py
```

### 10.2 Verify All Components
```bash
# Check all services are running
sudo systemctl status dual_recorder.service video_worker.service ezrec-api.service system_status.service

# Check all directories exist
ls -la /opt/ezrec-backend/

# Check environment variables
sudo cat /opt/ezrec-backend/.env | grep -v "^#" | grep -v "^$"

# Test API endpoints
curl http://localhost:8000/status
curl http://localhost:8000/bookings
```

## 📋 Success Checklist

### ✅ System Setup
- [ ] Raspberry Pi OS updated
- [ ] Python dependencies installed
- [ ] FFmpeg and camera tools installed
- [ ] Camera access configured
- [ ] Repository cloned and deployed

### ✅ Configuration
- [ ] Environment variables configured
- [ ] Camera serials set correctly
- [ ] Supabase credentials added
- [ ] AWS credentials added (if using S3)
- [ ] File permissions set correctly

### ✅ Camera Testing
- [ ] Cameras detected by v4l2-ctl
- [ ] Camera test suite passes
- [ ] Quick camera test successful
- [ ] Both cameras accessible

### ✅ Service Testing
- [ ] All services start without errors
- [ ] System health check passes
- [ ] Smoke test passes (5/5 tests)
- [ ] API server responds correctly

### ✅ Pipeline Testing
- [ ] Test booking created successfully
- [ ] Recording starts and stops correctly
- [ ] Video files created in recordings directory
- [ ] Processing pipeline works (merge, overlay, intro)
- [ ] Final output files created

### ✅ Monitoring
- [ ] Service logs show no errors
- [ ] System status monitoring works
- [ ] API endpoints respond correctly
- [ ] File permissions allow proper operation

## 🚨 Emergency Procedures

### If Services Won't Start
```bash
# Check systemd logs
sudo journalctl -xe

# Check service configuration
sudo systemctl cat dual_recorder.service

# Restart systemd
sudo systemctl daemon-reload
```

### If Cameras Don't Work
```bash
# Reboot Pi
sudo reboot

# Check camera modules
lsmod | grep v4l2

# Reinstall camera tools
sudo apt install --reinstall v4l-utils
```

### If Processing Fails
```bash
# Check FFmpeg
ffmpeg -version

# Reinstall FFmpeg
sudo apt install --reinstall ffmpeg

# Check disk space
df -h
```

## 📞 Support

If you encounter issues:

1. **Check the logs**: `sudo journalctl -u service_name -f`
2. **Run diagnostics**: `python3 test_system_health.py`
3. **Verify configuration**: Check all environment variables
4. **Test components individually**: Use the test scripts provided

## 🎯 Expected Results

After successful deployment, you should have:

- ✅ **2 cameras** recording simultaneously
- ✅ **Automatic booking detection** and recording start/stop
- ✅ **Video merging** with feathered blend
- ✅ **Logo overlays** and intro concatenation
- ✅ **Upload to cloud storage** (if configured)
- ✅ **Comprehensive logging** and monitoring
- ✅ **API endpoints** for booking management
- ✅ **Health monitoring** every 5 minutes

**Your EZREC system is now ready for production use!** 🚀 