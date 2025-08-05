# EZREC Backend Troubleshooting Guide

This guide addresses the recent issues with camera blank images, logo sizing, and live stream problems.

## Issues Fixed

### 1. Camera Producing Blank Images

**Problem**: Camera was producing black/blank images, likely due to camera initialization issues or process conflicts.

**Solution**: Enhanced `camera_streamer.py` with:

- Better camera initialization with retry logic
- Process conflict detection and resolution
- Black frame detection and automatic restart
- Improved error handling and logging

**Files Modified**:

- `backend/camera_streamer.py` - Enhanced with robust camera handling

### 2. Main Logo Too Large

**Problem**: The main EZREC logo was using the same size variables as other logos (120x120), making it too small.

**Solution**: Added separate environment variables for main logo sizing:

- `MAIN_LOGO_WIDTH=400`
- `MAIN_LOGO_HEIGHT=400`

**Files Modified**:

- `env.example` - Added new logo sizing variables
- `backend/video_worker.py` - Updated to use separate main logo sizing

### 3. Live Stream 502 Error

**Problem**: Live stream was returning 502 Bad Gateway errors due to camera_streamer service hanging.

**Solution**:

- Enhanced camera initialization with better error handling
- Added automatic camera restart on consecutive failures
- Improved process management

## New Tools Added

### 1. Camera Diagnostics Script

**File**: `backend/camera_diagnostics.py`

**Usage**:

```bash
cd /opt/ezrec-backend/backend
python3 camera_diagnostics.py
```

**Features**:

- Checks camera hardware and software status
- Identifies common issues and provides solutions
- Tests camera functionality
- Interactive troubleshooting

### 2. Service Restart Script

**File**: `backend/restart_services.sh`

**Usage**:

```bash
cd /opt/ezrec-backend/backend
sudo ./restart_services.sh
```

**Features**:

- Properly restarts all EZREC services in correct order
- Kills conflicting processes first
- Checks service status after restart
- Tests camera stream accessibility

## Environment Variables

### New Variables Added

Add these to your `.env` file:

```env
# Logo Sizing Configuration
LOGO_WIDTH=120
LOGO_HEIGHT=120
MAIN_LOGO_WIDTH=400
MAIN_LOGO_HEIGHT=400
```

### Existing Variables

Make sure these are properly set:

```env
RESOLUTION=1280x720
RECORDING_FPS=30
CAMERA_ID=your_camera_id
USER_ID=your_user_id
```

## Quick Fix Commands

### 1. Restart All Services

```bash
cd /opt/ezrec-backend/backend
sudo ./restart_services.sh
```

### 2. Run Camera Diagnostics

```bash
cd /opt/ezrec-backend/backend
python3 camera_diagnostics.py
```

### 3. Check Camera Stream

```bash
curl -I http://127.0.0.1:9000
```

### 4. View Camera Streamer Logs

```bash
sudo journalctl -u camera_streamer.service -f
```

### 5. Kill Camera Processes (if needed)

```bash
sudo pkill -f picamera2
sudo pkill -f camera_streamer
sudo systemctl restart camera_streamer.service
```

## Common Issues and Solutions

### Camera Shows Black Frames

1. Check camera lens cover
2. Ensure adequate lighting
3. Run camera diagnostics: `python3 camera_diagnostics.py`
4. Restart services: `sudo ./restart_services.sh`

### Camera Device Not Found

1. Check camera cable connection
2. Enable camera in raspi-config: `sudo raspi-config`
3. Reboot: `sudo reboot`

### Camera Locked by Another Process

1. Kill processes: `sudo pkill -f picamera2`
2. Restart camera service: `sudo systemctl restart camera_streamer.service`

### User Not in Video Group

1. Add user to video group: `sudo usermod -a -G video $USER`
2. Logout and login again

### Libraries Missing

1. Install picamera2: `sudo apt update && sudo apt install python3-picamera2`
2. Install Python libraries: `pip install opencv-python Pillow`

## Log Locations

- **Camera Streamer**: `sudo journalctl -u camera_streamer.service -f`
- **Recorder**: `sudo journalctl -u recorder.service -f`
- **Video Worker**: `sudo journalctl -u video_worker.service -f`
- **Status Updater**: `sudo journalctl -u status_updater.service -f`

## Testing

### Test Camera Stream

```bash
# Test local access
curl -I http://127.0.0.1:9000

# Test from frontend (if accessible)
curl -I http://your-raspberry-pi-ip:8000/live-preview
```

### Test Logo Sizing

1. Create a test recording
2. Check processed video for correct logo sizes
3. Main logo should be 400x400, others 120x120

## Deployment

After making changes:

1. **Update environment variables**:

   ```bash
   nano /opt/ezrec-backend/.env
   # Add the new logo sizing variables
   ```

2. **Restart services**:

   ```bash
   cd /opt/ezrec-backend/backend
   sudo ./restart_services.sh
   ```

3. **Test functionality**:
   ```bash
   python3 camera_diagnostics.py
   ```

## Support

If issues persist:

1. Run camera diagnostics
2. Check service logs
3. Verify environment variables
4. Test camera hardware independently
5. Check system resources (CPU, memory, temperature)
