# EZREC Backend - Professional Dual Camera Recording System

**Enterprise-grade automated dual-camera recording system for Raspberry Pi with modern service architecture**

## 📋 Table of Contents

- [🚀 Quick Start](#-quick-start)
- [🏗️ Architecture Overview](#️-architecture-overview)
- [📁 Project Structure](#-project-structure)
- [⚙️ Detailed Setup Guide](#️-detailed-setup-guide)
- [🔧 Configuration](#-configuration)
- [🎬 Recording System](#-recording-system)
- [📊 Monitoring & Health Checks](#-monitoring--health-checks)
- [🛠️ Development Guide](#️-development-guide)
- [🔧 Troubleshooting](#-troubleshooting)
- [📚 API Documentation](#-api-documentation)

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
   sudo python3 test.py
   ```

## 🏗️ Architecture Overview

EZREC uses a modern **service-oriented architecture** with clean separation of concerns:

### **Core Components**

- **🎥 Camera Service** - Handles camera detection and recording operations
- **📅 Booking Service** - Manages booking lifecycle and status tracking
- **🎬 Video Processor** - Handles video merging and processing
- **☁️ Upload Manager** - Manages file uploads to S3 and other storage
- **⚙️ Configuration System** - Centralized settings management
- **📝 Logging System** - Standardized logging across all services

### **Service Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Server    │    │  Dual Recorder  │    │  Video Worker   │
│   (FastAPI)     │    │    Service      │    │    Service      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Service Layer  │
                    │                 │
                    │ • Camera Service│
                    │ • Booking Service│
                    │ • Video Processor│
                    │ • Upload Manager│
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Configuration  │
                    │  & Utilities    │
                    │                 │
                    │ • Settings      │
                    │ • Logging       │
                    │ • Exceptions    │
                    └─────────────────┘
```

## 📁 Project Structure

```
EZREC-Backend-2/
├── 📋 README.md                    # This comprehensive documentation
├── 🚀 deployment.sh                # Single comprehensive deployment script
├── ⚙️ env.example                  # Environment variables template
├── 🧪 test.py                      # System testing script
├── 📝 logs.txt                     # Deployment and runtime logs
├── 📦 requirements.txt             # Python dependencies
│
├── ⚙️ config/                      # Centralized configuration
│   ├── __init__.py
│   └── settings.py                 # Single source of truth for all settings
│
├── 🏗️ services/                    # Service layer (business logic)
│   ├── __init__.py
│   ├── camera_service.py           # Camera operations and recording
│   ├── booking_service.py          # Booking management and status tracking
│   ├── video_processor.py          # Video processing and merging
│   └── upload_manager.py           # File uploads to S3 and storage
│
├── 🛠️ utils/                       # Shared utilities
│   ├── __init__.py
│   ├── logger.py                   # Standardized logging system
│   └── exceptions.py               # Custom exception classes
│
├── 🎥 backend/                     # Core backend services
│   ├── dual_recorder.py            # Main dual-camera recorder (refactored)
│   ├── booking_manager.py          # Enhanced booking management
│   ├── enhanced_merge.py           # Robust video merging with retry logic
│   ├── video_worker.py             # Video processing and upload worker
│   ├── system_status.py            # System monitoring and health checks
│   └── stitch/                     # Video stitching functionality
│       ├── __init__.py
│       ├── stitch_videos.py        # Panoramic video stitching
│       ├── calibrate_homography.py # Camera calibration
│       └── test_stitching.py       # Stitching tests
│
├── 🌐 api/                         # FastAPI web server
│   ├── api_server.py               # Main API server
│   └── templates/                  # HTML templates
│       └── share_video.html        # Video sharing template
│
└── ⚙️ systemd/                     # Service definitions
    ├── dual_recorder.service       # Dual camera recorder service
    ├── video_worker.service        # Video processing worker service
    ├── ezrec-api.service           # API server service
    ├── system_status.service       # System monitoring service
    └── system_status.timer         # System status timer
```

## ⚙️ Detailed Setup Guide

### **Prerequisites**

- **Raspberry Pi 4/5** with Raspberry Pi OS
- **Two compatible cameras** (IMX477, IMX219, etc.)
- **MicroSD card** (32GB+ recommended)
- **Internet connection** for initial setup

### **Hardware Setup**

1. **Connect Cameras**

   ```bash
   # Check camera detection
   v4l2-ctl --list-devices

   # Should show two cameras:
   # /dev/video0 - Camera 1
   # /dev/video1 - Camera 2
   ```

2. **Enable Camera Interface**
   ```bash
   sudo raspi-config
   # Navigate to: Interface Options > Camera > Enable
   # Reboot when prompted
   ```

### **Software Installation**

1. **Clone Repository**

   ```bash
   git clone https://github.com/naeimsalib/EZREC-BACKEND-2.git
   cd EZREC-BACKEND-2
   ```

2. **Run Deployment Script**

   ```bash
   chmod +x deployment.sh
   sudo ./deployment.sh
   ```

   The deployment script automatically:

   - Installs system dependencies (FFmpeg, v4l2-utils, etc.)
   - Sets up Python virtual environments
   - Creates required directories
   - Configures systemd services
   - Sets up cron jobs for maintenance
   - Tests system functionality

### **Environment Configuration**

1. **Create Environment File**

   ```bash
   sudo cp env.example /opt/ezrec-backend/.env
   sudo nano /opt/ezrec-backend/.env
   ```

2. **Configure Required Variables**

   ```bash
   # Supabase Configuration (Required)
   SUPABASE_URL=your_supabase_url_here
   SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here

   # AWS S3 Configuration (Required)
   AWS_ACCESS_KEY_ID=your_aws_access_key_here
   AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
   AWS_DEFAULT_REGION=us-east-1
   S3_BUCKET=your_s3_bucket_name_here

   # User Configuration (Required)
   USER_ID=your_user_id_here
   CAMERA_ID=your_camera_id_here
   ```

3. **Restart Services**
   ```bash
   sudo systemctl restart dual_recorder.service
   sudo systemctl restart video_worker.service
   sudo systemctl restart ezrec-api.service
   ```

## 🔧 Configuration

### **Centralized Configuration System**

EZREC uses a centralized configuration system in `config/settings.py`:

```python
from config.settings import settings

# Access configuration
database_url = settings.database.supabase_url
camera_width = settings.camera.recording_width
log_level = settings.logging.level
```

### **Configuration Categories**

#### **Database Configuration**

- Supabase URL and API keys
- Connection settings and timeouts

#### **Storage Configuration**

- AWS S3 credentials and bucket settings
- Upload configurations and retry policies

#### **Camera Configuration**

- Recording resolution and framerate
- Timeout settings and quality presets

#### **API Configuration**

- Server host and port settings
- Debug mode and logging levels

#### **Path Configuration**

- Deployment paths and directory structure
- Log file locations and permissions

### **Environment Variables**

| Variable                    | Required | Description               | Default |
| --------------------------- | -------- | ------------------------- | ------- |
| `SUPABASE_URL`              | ✅       | Supabase project URL      | -       |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅       | Supabase service role key | -       |
| `AWS_ACCESS_KEY_ID`         | ✅       | AWS access key            | -       |
| `AWS_SECRET_ACCESS_KEY`     | ✅       | AWS secret key            | -       |
| `S3_BUCKET`                 | ✅       | S3 bucket name            | -       |
| `USER_ID`                   | ✅       | User identifier           | -       |
| `CAMERA_ID`                 | ✅       | Camera identifier         | -       |
| `LOG_LEVEL`                 | ❌       | Logging level             | `INFO`  |
| `DEBUG`                     | ❌       | Debug mode                | `false` |

## 🎬 Recording System

### **Recording Lifecycle**

Each recording follows a structured lifecycle with status tracking:

```
📅 Scheduled → 🎥 Recording → ✅ Completed → 🎬 Processing → ☁️ Uploaded
```

### **Status Markers**

| Marker File  | Meaning                      | Next Action         |
| ------------ | ---------------------------- | ------------------- |
| `.lock`      | Recording in progress        | Wait for completion |
| `.done`      | Recording completed          | Start processing    |
| `.merged`    | Video merged successfully    | Start upload        |
| `.completed` | Fully processed and uploaded | Cleanup             |
| `.error`     | Error occurred               | Manual intervention |

### **Dual Camera Recording**

1. **Camera Detection**: Automatically detects available cameras
2. **Synchronized Recording**: Records from both cameras simultaneously
3. **Automatic Merging**: Merges videos using FFmpeg or panoramic stitching
4. **Quality Validation**: Validates output files before upload
5. **Error Handling**: Retries failed operations with exponential backoff

### **Video Processing Pipeline**

```
Raw Videos → Validation → Merging → Compression → Upload → Cleanup
```

- **Validation**: Checks file integrity and metadata
- **Merging**: Combines dual camera feeds (side-by-side or panoramic)
- **Compression**: Optimizes file size for storage and streaming
- **Upload**: Transfers to S3 with progress tracking
- **Cleanup**: Removes temporary files and updates status

## 📊 Monitoring & Health Checks

### **System Health Endpoints**

- `GET /health` - Comprehensive system health check
- `GET /status` - System status and metrics
- `GET /recording-logs` - Recent recording activity
- `GET /booking-stats` - Booking statistics and trends

### **Health Check Components**

```bash
# Run comprehensive health check
sudo python3 test.py
```

Tests include:

- ✅ Environment variables validation
- ✅ Required directories and permissions
- ✅ FFmpeg, FFprobe, v4l2-ctl availability
- ✅ Camera device detection
- ✅ API server health
- ✅ Systemd services status
- ✅ Database connectivity
- ✅ S3 storage access

### **Service Monitoring**

```bash
# Check service status
sudo systemctl status dual_recorder.service
sudo systemctl status video_worker.service
sudo systemctl status ezrec-api.service

# View real-time logs
sudo journalctl -u dual_recorder.service -f
sudo journalctl -u video_worker.service -f
sudo journalctl -u ezrec-api.service -f
```

### **Log Management**

- **Centralized Logging**: All services use standardized logging
- **Log Rotation**: Automatic log rotation and cleanup
- **Structured Logs**: JSON-formatted logs for easy parsing
- **Log Levels**: Configurable logging levels per service

## 🛠️ Development Guide

### **Service Development**

1. **Create New Service**

   ```python
   from services.base_service import BaseService
   from utils.logger import get_logger
   from utils.exceptions import handle_exception

   class MyService(BaseService):
       def __init__(self):
           super().__init__()
           self.logger = get_logger(__name__)

       @handle_exception
       def my_method(self):
           # Service implementation
           pass
   ```

2. **Add Configuration**

   ```python
   # In config/settings.py
   @dataclass
   class MyServiceConfig:
       my_setting: str = "default_value"

   class Settings:
       def __init__(self):
           # ... existing configs ...
           self.my_service = MyServiceConfig()
   ```

3. **Add Exception Handling**
   ```python
   # In utils/exceptions.py
   class MyServiceError(EZRECException):
       """My service specific errors"""
       pass
   ```

### **Testing**

```bash
# Run system tests
python3 test.py

# Test specific components
python3 -m pytest tests/

# Test with verbose output
python3 test.py --verbose
```

### **Code Quality**

- **Type Hints**: All functions include type annotations
- **Documentation**: Comprehensive docstrings for all classes and methods
- **Error Handling**: Structured exception handling with context
- **Logging**: Consistent logging across all services
- **Testing**: Unit tests for critical functionality

## 🔧 Troubleshooting

### **Common Issues**

#### **1. Camera Not Detected**

```bash
# Check camera devices
v4l2-ctl --list-devices

# Test camera access
sudo python3 -c "
from services.camera_service import CameraService
service = CameraService()
cameras = service.detect_cameras()
print(f'Detected cameras: {cameras}')
"

# Check permissions
ls -la /dev/video*
sudo usermod -a -G video $USER
```

#### **2. Service Not Starting**

```bash
# Check service status
sudo systemctl status dual_recorder.service

# View detailed logs
sudo journalctl -u dual_recorder.service -n 100

# Check configuration
sudo python3 -c "
from config.settings import settings
print('Configuration valid:', settings.database.validate())
"
```

#### **3. Recording Failures**

```bash
# Check camera health
sudo python3 backend/camera_health_check.py --verbose

# Test recording manually
rpicam-vid --camera 0 --timeout 5000 --output /tmp/test.mp4

# Check disk space
df -h /opt/ezrec-backend/recordings
```

#### **4. Upload Issues**

```bash
# Test S3 connectivity
sudo python3 -c "
from services.upload_manager import UploadManager
manager = UploadManager()
print('S3 status:', manager.get_upload_stats())
"

# Check AWS credentials
aws s3 ls s3://your-bucket-name
```

### **Log Analysis**

```bash
# View recent errors
sudo journalctl -u dual_recorder.service --since "1 hour ago" | grep ERROR

# Monitor recording activity
tail -f /opt/ezrec-backend/logs/dual_recorder.log

# Check system health
curl http://localhost:8000/health | jq
```

### **Performance Optimization**

```bash
# Check system resources
htop
iostat -x 1

# Monitor disk I/O
iotop

# Check network usage
iftop
```

## 📚 API Documentation

### **Core Endpoints**

#### **Health & Status**

- `GET /health` - System health check
- `GET /status` - Service status and metrics
- `GET /system-info` - System information

#### **Recording Management**

- `POST /bookings` - Create new booking
- `GET /bookings` - List all bookings
- `GET /bookings/{id}` - Get specific booking
- `PUT /bookings/{id}` - Update booking
- `DELETE /bookings/{id}` - Delete booking

#### **Video Management**

- `GET /videos` - List recorded videos
- `GET /videos/{id}` - Get video details
- `POST /videos/{id}/share` - Create share link
- `DELETE /videos/{id}` - Delete video

#### **System Management**

- `POST /system/restart` - Restart services
- `GET /system/logs` - Get system logs
- `POST /system/cleanup` - Run cleanup tasks

### **Response Formats**

All API responses follow a consistent format:

```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully",
  "timestamp": "2025-01-14T10:30:00Z"
}
```

Error responses:

```json
{
  "success": false,
  "error": "ErrorType",
  "message": "Human readable error message",
  "details": { ... },
  "timestamp": "2025-01-14T10:30:00Z"
}
```

## 🎯 Key Features

- ✅ **Modern Service Architecture** - Clean separation of concerns
- ✅ **Centralized Configuration** - Single source of truth for all settings
- ✅ **Robust Error Handling** - Structured exceptions with retry logic
- ✅ **Comprehensive Logging** - Standardized logging across all services
- ✅ **Health Monitoring** - Real-time system health and status tracking
- ✅ **Automatic Recovery** - Self-healing services with restart policies
- ✅ **Scalable Design** - Easy to extend and modify
- ✅ **Production Ready** - Enterprise-grade reliability and performance

## 📄 License

This project is licensed under the MIT License.

---

**Made with ❤️ for professional video recording on Raspberry Pi**

_For support and questions, please refer to the troubleshooting section or create an issue on GitHub._
