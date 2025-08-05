# EZREC Backend - Consolidated Architecture

## Overview

The EZREC backend has been consolidated to use existing, proven services rather than creating duplicate functionality. This approach leverages the robust existing codebase while maintaining clean separation of concerns.

## Core Services

### 1. **Dual Recorder Service** (`dual_recorder.py`)
- **Purpose**: Handles dual camera recording with advanced error handling
- **Features**: 
  - Direct camera detection and initialization
  - Thread-safe recording with health monitoring
  - Automatic camera cleanup and resource management
  - Booking integration via `booking_utils.py`
  - Enhanced merge functionality using `enhanced_merge.py`
- **Configuration**: Environment variables for camera serials, resolution, bitrate
- **Output**: Individual camera recordings and merged videos

### 2. **Video Worker Service** (`video_worker.py`)
- **Purpose**: Comprehensive video processing and upload pipeline
- **Features**:
  - Logo overlay processing (sponsor and company logos)
  - Intro video concatenation
  - Video validation and repair
  - Chunked upload to S3/Cloudflare R2
  - Database metadata management
  - Retry logic with exponential backoff
- **Processing Flow**: Raw video → Logo overlays → Intro concatenation → Upload
- **Configuration**: User media from Supabase, AWS credentials

### 3. **API Server** (`api_server.py`)
- **Purpose**: FastAPI backend for booking management and status
- **Features**:
  - Booking CRUD operations
  - Camera status monitoring
  - Share link generation
  - User media management
- **Integration**: Uses `booking_utils.py` for database operations

### 4. **System Status Service** (`system_status.py`)
- **Purpose**: Health monitoring and system diagnostics
- **Features**:
  - Disk space monitoring
  - Service health checks
  - Camera status reporting
  - Performance metrics
- **Schedule**: Runs every 5 minutes via systemd timer

## Directory Structure

```
/opt/ezrec-backend/
├── backend/
│   ├── dual_recorder.py          # Main recording service
│   ├── video_worker.py           # Video processing service
│   ├── enhanced_merge.py         # Advanced video merging
│   ├── booking_manager.py        # Booking management
│   ├── camera_health_check.py    # Camera diagnostics
│   └── system_status.py          # Health monitoring
├── api/
│   ├── api_server.py             # FastAPI backend
│   ├── booking_utils.py          # Booking utilities
│   └── monitor.py                # API monitoring
├── systemd/
│   ├── dual_recorder.service     # Recording service
│   ├── video_worker.service      # Processing service
│   ├── ezrec-api.service         # API service
│   ├── system_status.service     # Health service
│   └── system_status.timer       # Health timer
├── recordings/                   # Raw camera recordings
├── processed/                    # Videos with overlays
├── final/                       # Final videos with intro
├── assets/                      # Logos and intro videos
└── logs/                        # Service logs
```

## Service Dependencies

```
dual_recorder.py
├── booking_utils.py (API)
├── enhanced_merge.py
└── camera_health_check.py

video_worker.py
├── booking_utils.py (API)
├── enhanced_merge.py
└── AWS S3/Cloudflare R2

api_server.py
├── booking_utils.py
└── Supabase Database

system_status.py
└── All services (monitoring)
```

## Processing Flow

### 1. **Recording Phase**
```
Booking Start → dual_recorder.py → Camera Detection → Recording → Merge → .done marker
```

### 2. **Processing Phase**
```
.done marker → video_worker.py → Logo Overlays → Intro Concatenation → Upload → Database
```

### 3. **Monitoring Phase**
```
system_status.py → Health Check → Logging → Alerting
```

## Configuration

### Environment Variables
```bash
# Core Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_key
USER_ID=your_user_id
CAMERA_ID=your_camera_id

# Camera Configuration
CAMERA_0_SERIAL=your_first_camera_serial
CAMERA_1_SERIAL=your_second_camera_serial
DUAL_CAMERA_MODE=true

# Recording Configuration
RECORDING_FPS=30
MERGE_METHOD=side_by_side

# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_S3_BUCKET=your_s3_bucket
```

## Deployment

### 1. **Systemd Services**
The deployment script automatically installs systemd services from the `systemd/` folder:
- `dual_recorder.service` - Main recording service
- `video_worker.service` - Video processing service  
- `ezrec-api.service` - API backend service
- `system_status.service` - Health monitoring service

### 2. **Service Management**
```bash
# Start all services
sudo systemctl start dual_recorder.service video_worker.service ezrec-api.service

# Check status
sudo systemctl status dual_recorder.service video_worker.service ezrec-api.service

# View logs
sudo journalctl -u dual_recorder.service -f
sudo journalctl -u video_worker.service -f
```

## Error Handling

### 1. **Recording Errors**
- Camera detection failures → Fallback to single camera
- Recording failures → Automatic retry with exponential backoff
- Merge failures → Fallback to individual camera files

### 2. **Processing Errors**
- Logo overlay failures → Skip overlays, continue processing
- Intro concatenation failures → Skip intro, continue processing
- Upload failures → Retry with exponential backoff

### 3. **System Errors**
- Service crashes → Automatic restart via systemd
- Disk space issues → Automatic cleanup of old files
- Network issues → Graceful degradation

## Monitoring

### 1. **Service Health**
```bash
# Check all services
sudo systemctl status dual_recorder.service video_worker.service ezrec-api.service

# View recent logs
sudo journalctl -u dual_recorder.service --since "1 hour ago"
```

### 2. **System Health**
```bash
# Check disk space
df -h /opt/ezrec-backend

# Check camera status
sudo v4l2-ctl --list-devices

# Check recording files
ls -la /opt/ezrec-backend/recordings/
```

## Troubleshooting

### Common Issues

1. **Camera Not Detected**
   ```bash
   # Check camera hardware
   sudo v4l2-ctl --list-devices
   
   # Test camera access
   python3 /opt/ezrec-backend/backend/quick_camera_test.py
   ```

2. **Recording Failures**
   ```bash
   # Check dual recorder logs
   sudo journalctl -u dual_recorder.service -f
   
   # Check disk space
   df -h /opt/ezrec-backend
   ```

3. **Processing Failures**
   ```bash
   # Check video worker logs
   sudo journalctl -u video_worker.service -f
   
   # Check file permissions
   ls -la /opt/ezrec-backend/processed/
   ```

4. **Upload Failures**
   ```bash
   # Check AWS credentials
   aws s3 ls s3://your-bucket/
   
   # Check network connectivity
   ping 8.8.8.8
   ```

## Benefits of Consolidated Architecture

1. **Reduced Complexity**: Uses existing, proven services instead of creating duplicates
2. **Better Maintainability**: Single source of truth for each functionality
3. **Improved Reliability**: Leverages battle-tested code with extensive error handling
4. **Easier Deployment**: Fewer services to manage and monitor
5. **Better Resource Usage**: Optimized for Raspberry Pi deployment

## Migration Notes

- **Removed Services**: `dual_camera.py`, `booking_watcher.py`, `stitcher.py`, `video_processor.py`, `uploader.py`
- **Enhanced Services**: `dual_recorder.py`, `video_worker.py` with additional features
- **Systemd Files**: Moved to `systemd/` folder for better organization
- **Deployment**: Updated to use existing services with proper systemd integration 