# EZREC Modular Architecture

This document describes the new modular architecture for the EZREC dual camera recording system.

## Overview

The system has been refactored into separate, focused services that work together to provide a complete dual camera recording solution. Each service has a specific responsibility and communicates with others through file-based events and shared directories.

## Service Architecture

### 1. Dual Camera Service (`dual_camera.py`)

**Purpose**: Records from both cameras simultaneously using Picamera2

**Configuration**:
```python
CAM_IDS = [0, 1]
RESOLUTION = (1920, 1080)  # Full HD
FRAMERATE = 30
BITRATE = 6_000_000  # 6 Mbps
OUTPUT_DIR = "/opt/ezrec-backend/recordings"
```

**Key Features**:
- Direct camera detection and initialization
- Thread-safe recording for each camera
- Proper camera cleanup to prevent stuck processes
- H.264 encoding with configurable bitrate
- Event emission for recording completion

**Output**: Two H.264 files per booking (cam0.h264, cam1.h264)

### 2. Booking Watcher Service (`booking_watcher.py`)

**Purpose**: Monitors booking cache and manages recording state transitions

**Key Features**:
- Reads `booking_cache.json` every 5 seconds
- Detects active bookings for current user/camera
- Emits start/stop recording events
- Updates booking status in database
- Handles recording complete events

**Events Emitted**:
- `start_recording.event` - Triggers recording start
- `stop_recording.event` - Triggers recording stop

### 3. Video Stitcher Service (`stitcher.py`)

**Purpose**: Post-record stitching with feathered blend and fallback options

**Key Features**:
- OpenCV-based feathered blend stitching
- FFmpeg fallback for hstack merging
- Automatic detection of video pairs
- Validation of input files
- Progress logging and error handling

**Processing Flow**:
1. Detects pairs of camera recordings
2. Converts H.264 to MP4
3. Performs feathered blend or hstack merge
4. Outputs merged video with `_stitched` suffix

### 4. Video Processor Service (`video_processor.py`)

**Purpose**: Adds overlays and intro video to processed recordings

**Key Features**:
- Logo overlay using FFmpeg
- Intro video concatenation
- Asset management (logos, intro video)
- Fallback handling for missing assets

**Processing Flow**:
1. Adds sponsor and company logos
2. Concatenates intro video
3. Outputs final video with `_final` suffix

### 5. Video Uploader Service (`uploader.py`)

**Purpose**: Uploads final videos to cloud storage with retry logic

**Key Features**:
- AWS S3 and Supabase Storage support
- Exponential backoff retry logic
- Chunked uploads for large files
- Database metadata updates
- Upload completion markers

**Upload Flow**:
1. Validates final video files
2. Uploads to configured storage
3. Updates database with metadata
4. Creates `.uploaded` marker

### 6. Legacy Services

**Video Worker Service (`video_worker.py`)**: Maintained for backward compatibility
**API Server (`api_server.py`)**: FastAPI backend for web interface
**System Status Service (`system_status.py`)**: System health monitoring

## Directory Structure

```
/opt/ezrec-backend/
├── recordings/          # Raw camera recordings
├── processed/          # Stitched videos
├── final/             # Videos with overlays and intro
├── assets/            # Logos and intro video
├── logs/              # Service logs
├── api/               # API server
└── backend/           # Service scripts
```

## File Naming Convention

**Camera Recordings**: `{timestamp}_{booking_id}_cam{0|1}.h264`
**Stitched Videos**: `{timestamp}_{booking_id}_stitched.mp4`
**Final Videos**: `{timestamp}_{booking_id}_final.mp4`

## Event System

Services communicate through file-based events:

- `start_recording.event` - JSON with booking details
- `stop_recording.event` - JSON with booking ID
- `recording_complete.event` - JSON with file paths
- `.uploaded` marker - Indicates successful upload

## Configuration

Environment variables in `/opt/ezrec-backend/.env`:

```bash
# Camera Configuration
CAMERA_0_SERIAL=88000
CAMERA_1_SERIAL=80000
DUAL_CAMERA_MODE=true

# Recording Configuration
RECORDING_QUALITY=high
MERGE_METHOD=side_by_side

# AWS Configuration
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_S3_BUCKET=your_bucket

# Supabase Configuration
SUPABASE_URL=your_url
SUPABASE_SERVICE_ROLE_KEY=your_key
```

## Service Dependencies

```
booking_watcher → dual_camera → stitcher → video_processor → uploader
     ↓              ↓            ↓            ↓              ↓
  events       recordings   processed    final        cloud storage
```

## Deployment

The `deployment.sh` script handles:

1. Service installation and configuration
2. Directory creation and permissions
3. Systemd service setup
4. Asset creation
5. Service startup and validation

## Monitoring

Each service logs to `/opt/ezrec-backend/logs/` with rotating file handlers:

- `dual_camera.log`
- `booking_watcher.log`
- `stitcher.log`
- `video_processor.log`
- `uploader.log`

## Error Handling

- **Camera Failures**: Graceful degradation to single camera
- **Stitching Failures**: Fallback to simple hstack
- **Upload Failures**: Exponential backoff retry
- **Asset Missing**: Skip overlay/concatenation
- **Service Crashes**: Automatic restart via systemd

## Performance Considerations

- **Memory**: Each service runs independently
- **CPU**: FFmpeg operations are CPU-intensive
- **Storage**: Videos are cleaned up after processing
- **Network**: Uploads use chunked transfer

## Troubleshooting

1. **Check service status**: `sudo systemctl status dual_camera.service`
2. **View logs**: `sudo journalctl -u dual_camera.service -f`
3. **Test camera**: `python3 backend/test_camera_detection.py`
4. **Check disk space**: `df -h /opt/ezrec-backend/`
5. **Validate files**: Check for `.error` markers in output directories

## Migration from Legacy

The new architecture maintains backward compatibility:

- Existing `dual_recorder.py` continues to work
- `video_worker.py` processes legacy files
- Database schema unchanged
- API endpoints remain the same

## Future Enhancements

- **Real-time streaming**: WebRTC integration
- **AI processing**: Object detection and tracking
- **Cloud processing**: Offload heavy operations
- **Multi-camera support**: More than 2 cameras
- **Advanced stitching**: 360° video support 