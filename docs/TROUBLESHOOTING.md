# EZREC Troubleshooting Guide

**Comprehensive troubleshooting guide for the EZREC dual-camera recording system**

## 📋 Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Camera Issues](#camera-issues)
- [Service Issues](#service-issues)
- [Recording Problems](#recording-problems)
- [Upload Issues](#upload-issues)
- [Performance Problems](#performance-problems)
- [Network Issues](#network-issues)
- [Configuration Problems](#configuration-problems)
- [Log Analysis](#log-analysis)
- [Emergency Recovery](#emergency-recovery)

## Quick Diagnostics

### **System Health Check**

```bash
# Run comprehensive system test
sudo python3 test.py

# Check service status
sudo systemctl status dual_recorder.service video_worker.service ezrec-api.service

# Check system resources
htop
df -h
free -h
```

### **Quick Status Commands**

```bash
# Check if cameras are detected
v4l2-ctl --list-devices

# Check if services are running
sudo systemctl is-active dual_recorder.service
sudo systemctl is-active video_worker.service
sudo systemctl is-active ezrec-api.service

# Check recent logs
sudo journalctl -u dual_recorder.service --since "10 minutes ago"
```

## Camera Issues

### **Problem: No Cameras Detected**

**Symptoms:**
- `v4l2-ctl --list-devices` shows no cameras
- Service logs show "No cameras available"
- Recording fails immediately

**Diagnosis:**
```bash
# Check camera interface
sudo raspi-config
# Navigate to: Interface Options > Camera > Enable

# Check camera connections
ls -la /dev/video*

# Check camera modules
lsmod | grep bcm2835
```

**Solutions:**

1. **Enable Camera Interface**
   ```bash
   sudo raspi-config
   # Interface Options > Camera > Enable
   sudo reboot
   ```

2. **Check Physical Connections**
   - Ensure cameras are properly connected to CSI ports
   - Check ribbon cable connections
   - Try different cameras if available

3. **Update Firmware**
   ```bash
   sudo apt update
   sudo apt upgrade -y
   sudo rpi-update
   sudo reboot
   ```

### **Problem: Camera Initialization Failed**

**Symptoms:**
- Camera detected but recording fails
- Error: "Camera in Acquired state trying acquire()"
- Service crashes on startup

**Diagnosis:**
```bash
# Check for camera processes
ps aux | grep -i camera
ps aux | grep -i libcamera

# Kill existing camera processes
sudo pkill -f camera
sudo pkill -f libcamera
sudo pkill -f picamera2
```

**Solutions:**

1. **Kill Existing Processes**
   ```bash
   sudo pkill -f camera
   sudo pkill -f libcamera
   sudo pkill -f picamera2
   sudo systemctl restart dual_recorder.service
   ```

2. **Reset Camera State**
   ```bash
   sudo modprobe -r bcm2835_v4l2
   sudo modprobe bcm2835_v4l2
   ```

3. **Check Camera Permissions**
   ```bash
   sudo usermod -a -G video $USER
   sudo chmod 666 /dev/video*
   ```

### **Problem: Poor Video Quality**

**Symptoms:**
- Blurry or distorted video
- Low frame rate
- Audio sync issues

**Diagnosis:**
```bash
# Check camera settings
rpicam-vid --list-cameras

# Test camera manually
rpicam-vid --camera 0 --width 1280 --height 720 --framerate 30 --timeout 5000 --output /tmp/test.mp4
```

**Solutions:**

1. **Adjust Camera Settings**
   ```bash
   # Edit camera configuration
   sudo nano /opt/ezrec-backend/config/settings.py
   
   # Increase quality settings
   recording_width: 1920
   recording_height: 1080
   recording_framerate: 30
   ```

2. **Check Lighting Conditions**
   - Ensure adequate lighting
   - Avoid direct sunlight
   - Use consistent lighting

3. **Update Camera Drivers**
   ```bash
   sudo apt update
   sudo apt install --reinstall libcamera-tools
   ```

## Service Issues

### **Problem: Service Won't Start**

**Symptoms:**
- `systemctl status` shows "failed"
- Service exits immediately
- No logs generated

**Diagnosis:**
```bash
# Check service status
sudo systemctl status dual_recorder.service

# Check service logs
sudo journalctl -u dual_recorder.service -n 50

# Check service file
sudo systemctl cat dual_recorder.service
```

**Solutions:**

1. **Check Service File**
   ```bash
   # Verify service file exists and is correct
   sudo systemctl cat dual_recorder.service
   
   # Reload systemd
   sudo systemctl daemon-reload
   ```

2. **Check Dependencies**
   ```bash
   # Verify Python environment
   sudo -u root /opt/ezrec-backend/venv/bin/python3 -c "import sys; print(sys.path)"
   
   # Check file permissions
   ls -la /opt/ezrec-backend/backend/dual_recorder.py
   ```

3. **Manual Service Start**
   ```bash
   # Start service manually to see errors
   sudo -u root /opt/ezrec-backend/venv/bin/python3 /opt/ezrec-backend/backend/dual_recorder.py
   ```

### **Problem: Service Keeps Restarting**

**Symptoms:**
- Service status shows "activating"
- Frequent restarts in logs
- High CPU usage

**Diagnosis:**
```bash
# Check restart count
sudo systemctl show dual_recorder.service | grep RestartCount

# Check service logs for crash patterns
sudo journalctl -u dual_recorder.service --since "1 hour ago" | grep -E "(error|exception|traceback)"
```

**Solutions:**

1. **Check for Resource Issues**
   ```bash
   # Check memory usage
   free -h
   
   # Check disk space
   df -h
   
   # Check CPU usage
   top
   ```

2. **Increase Restart Delay**
   ```bash
   # Edit service file
   sudo systemctl edit dual_recorder.service
   
   # Add:
   [Service]
   RestartSec=10
   ```

3. **Check for Configuration Errors**
   ```bash
   # Validate configuration
   sudo python3 -c "
   from config.settings import settings
   print('Config valid:', settings.database.validate())
   "
   ```

## Recording Problems

### **Problem: Recording Files Not Created**

**Symptoms:**
- No video files in recordings directory
- Service logs show recording started but no files
- Disk space available but no output

**Diagnosis:**
```bash
# Check recordings directory
ls -la /opt/ezrec-backend/recordings/

# Check disk space
df -h /opt/ezrec-backend/recordings/

# Check permissions
ls -la /opt/ezrec-backend/recordings/
```

**Solutions:**

1. **Check Directory Permissions**
   ```bash
   # Fix permissions
   sudo chown -R root:root /opt/ezrec-backend/recordings/
   sudo chmod -R 755 /opt/ezrec-backend/recordings/
   ```

2. **Check Disk Space**
   ```bash
   # Clean up old files
   sudo find /opt/ezrec-backend/recordings/ -name "*.mp4" -mtime +7 -delete
   
   # Check available space
   df -h
   ```

3. **Test Manual Recording**
   ```bash
   # Test recording manually
   rpicam-vid --camera 0 --timeout 10000 --output /tmp/test.mp4
   ls -la /tmp/test.mp4
   ```

### **Problem: Recording Stops Prematurely**

**Symptoms:**
- Recording starts but stops before booking end time
- Partial video files created
- Service logs show unexpected termination

**Diagnosis:**
```bash
# Check service logs
sudo journalctl -u dual_recorder.service --since "1 hour ago"

# Check for system issues
dmesg | tail -20

# Check memory usage
free -h
```

**Solutions:**

1. **Check System Resources**
   ```bash
   # Monitor memory usage
   watch -n 1 free -h
   
   # Check for memory leaks
   sudo journalctl -u dual_recorder.service | grep -i memory
   ```

2. **Increase Timeout Settings**
   ```bash
   # Edit camera configuration
   sudo nano /opt/ezrec-backend/config/settings.py
   
   # Increase timeout
   recording_timeout: 600000  # 10 minutes
   ```

3. **Check for Interference**
   ```bash
   # Check for other processes using cameras
   lsof /dev/video*
   
   # Kill interfering processes
   sudo pkill -f v4l2
   ```

## Upload Issues

### **Problem: S3 Upload Fails**

**Symptoms:**
- Videos recorded but not uploaded
- Error messages about AWS credentials
- Upload timeout errors

**Diagnosis:**
```bash
# Check AWS credentials
aws configure list

# Test S3 connectivity
aws s3 ls s3://your-bucket-name

# Check network connectivity
ping s3.amazonaws.com
```

**Solutions:**

1. **Verify AWS Credentials**
   ```bash
   # Check environment variables
   sudo cat /opt/ezrec-backend/.env | grep AWS
   
   # Test credentials
   aws sts get-caller-identity
   ```

2. **Check Network Connectivity**
   ```bash
   # Test internet connection
   curl -I https://s3.amazonaws.com
   
   # Check DNS resolution
   nslookup s3.amazonaws.com
   ```

3. **Check S3 Bucket Configuration**
   ```bash
   # Verify bucket exists and is accessible
   aws s3 ls s3://your-bucket-name
   
   # Check bucket permissions
   aws s3api get-bucket-acl --bucket your-bucket-name
   ```

### **Problem: Upload Timeout**

**Symptoms:**
- Upload starts but never completes
- Large files fail to upload
- Network timeout errors

**Diagnosis:**
```bash
# Check network speed
speedtest-cli

# Check upload progress
sudo journalctl -u video_worker.service | grep -i upload
```

**Solutions:**

1. **Optimize Upload Settings**
   ```bash
   # Edit upload configuration
   sudo nano /opt/ezrec-backend/services/upload_manager.py
   
   # Increase timeout
   timeout=600  # 10 minutes
   ```

2. **Compress Videos Before Upload**
   ```bash
   # Enable video compression
   sudo nano /opt/ezrec-backend/config/settings.py
   
   # Add compression settings
   video_compression: true
   compression_quality: "medium"
   ```

3. **Use Multipart Upload**
   ```bash
   # Enable multipart upload for large files
   sudo nano /opt/ezrec-backend/services/upload_manager.py
   
   # Add multipart settings
   multipart_threshold: 100 * 1024 * 1024  # 100MB
   ```

## Performance Problems

### **Problem: High CPU Usage**

**Symptoms:**
- System becomes unresponsive
- High CPU usage during recording
- Slow video processing

**Diagnosis:**
```bash
# Check CPU usage
top
htop

# Check process details
ps aux --sort=-%cpu | head -10

# Check system load
uptime
```

**Solutions:**

1. **Optimize Recording Settings**
   ```bash
   # Reduce recording quality
   sudo nano /opt/ezrec-backend/config/settings.py
   
   # Lower settings
   recording_width: 1280
   recording_height: 720
   recording_framerate: 24
   ```

2. **Limit Background Processes**
   ```bash
   # Disable unnecessary services
   sudo systemctl disable bluetooth
   sudo systemctl disable cups
   sudo systemctl disable avahi-daemon
   ```

3. **Add CPU Governor**
   ```bash
   # Set CPU governor to performance
   echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
   ```

### **Problem: High Memory Usage**

**Symptoms:**
- System runs out of memory
- Services killed by OOM killer
- Slow system performance

**Diagnosis:**
```bash
# Check memory usage
free -h
cat /proc/meminfo

# Check for memory leaks
sudo journalctl -u dual_recorder.service | grep -i memory
```

**Solutions:**

1. **Increase Swap Space**
   ```bash
   # Create swap file
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   
   # Make permanent
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   ```

2. **Optimize Memory Usage**
   ```bash
   # Edit service configuration
   sudo nano /opt/ezrec-backend/config/settings.py
   
   # Reduce buffer sizes
   buffer_size: 1024 * 1024  # 1MB
   ```

3. **Monitor Memory Usage**
   ```bash
   # Add memory monitoring
   sudo crontab -e
   
   # Add:
   */5 * * * * /usr/bin/free -h >> /opt/ezrec-backend/logs/memory.log
   ```

## Network Issues

### **Problem: API Not Accessible**

**Symptoms:**
- Cannot access API endpoints
- Connection refused errors
- Service running but not responding

**Diagnosis:**
```bash
# Check if API service is running
sudo systemctl status ezrec-api.service

# Check if port is listening
sudo netstat -tlnp | grep 8000

# Test local connection
curl http://localhost:8000/health
```

**Solutions:**

1. **Check Firewall Settings**
   ```bash
   # Check firewall status
   sudo ufw status
   
   # Allow API port
   sudo ufw allow 8000/tcp
   ```

2. **Check Service Configuration**
   ```bash
   # Check service file
   sudo systemctl cat ezrec-api.service
   
   # Restart service
   sudo systemctl restart ezrec-api.service
   ```

3. **Check Network Interface**
   ```bash
   # Check network configuration
   ip addr show
   
   # Check routing
   ip route show
   ```

### **Problem: Slow Network Performance**

**Symptoms:**
- Slow upload speeds
- Timeout errors
- Intermittent connectivity

**Diagnosis:**
```bash
# Test network speed
speedtest-cli

# Check network interface
ethtool eth0

# Check for packet loss
ping -c 100 google.com
```

**Solutions:**

1. **Optimize Network Settings**
   ```bash
   # Edit network configuration
   sudo nano /etc/dhcpcd.conf
   
   # Add network optimizations
   interface eth0
   static ip_address=192.168.1.100/24
   static routers=192.168.1.1
   static domain_name_servers=8.8.8.8 8.8.4.4
   ```

2. **Check Network Hardware**
   ```bash
   # Check network interface status
   sudo ethtool eth0
   
   # Check for errors
   cat /proc/net/dev
   ```

3. **Optimize Upload Settings**
   ```bash
   # Edit upload configuration
   sudo nano /opt/ezrec-backend/services/upload_manager.py
   
   # Add network optimizations
   max_concurrency: 2
   chunk_size: 8 * 1024 * 1024  # 8MB
   ```

## Configuration Problems

### **Problem: Environment Variables Not Loaded**

**Symptoms:**
- Services fail to start
- Database connection errors
- Missing configuration values

**Diagnosis:**
```bash
# Check environment file
sudo cat /opt/ezrec-backend/.env

# Check if variables are loaded
sudo -u root /opt/ezrec-backend/venv/bin/python3 -c "
import os
print('SUPABASE_URL:', os.getenv('SUPABASE_URL'))
print('AWS_ACCESS_KEY_ID:', os.getenv('AWS_ACCESS_KEY_ID'))
"
```

**Solutions:**

1. **Verify Environment File**
   ```bash
   # Check file permissions
   ls -la /opt/ezrec-backend/.env
   
   # Check file content
   sudo cat /opt/ezrec-backend/.env
   ```

2. **Reload Environment**
   ```bash
   # Restart services to reload environment
   sudo systemctl restart dual_recorder.service
   sudo systemctl restart video_worker.service
   sudo systemctl restart ezrec-api.service
   ```

3. **Check Configuration Validation**
   ```bash
   # Test configuration
   sudo python3 -c "
   from config.settings import settings
   print('Database valid:', settings.database.validate())
   print('Storage valid:', settings.storage.validate())
   "
   ```

### **Problem: Service Configuration Errors**

**Symptoms:**
- Services fail to start
- Configuration validation errors
- Incorrect service behavior

**Diagnosis:**
```bash
# Check service files
sudo systemctl cat dual_recorder.service
sudo systemctl cat video_worker.service
sudo systemctl cat ezrec-api.service

# Check configuration files
sudo cat /opt/ezrec-backend/config/settings.py
```

**Solutions:**

1. **Validate Service Files**
   ```bash
   # Check service file syntax
   sudo systemctl daemon-reload
   sudo systemctl status dual_recorder.service
   ```

2. **Check File Permissions**
   ```bash
   # Fix permissions
   sudo chown -R root:root /opt/ezrec-backend
   sudo chmod -R 755 /opt/ezrec-backend
   sudo chmod +x /opt/ezrec-backend/backend/*.py
   ```

3. **Restore Default Configuration**
   ```bash
   # Restore from backup
   sudo cp /opt/ezrec-backend/config/settings.py.backup /opt/ezrec-backend/config/settings.py
   
   # Or recreate from template
   sudo cp /opt/ezrec-backend/env.example /opt/ezrec-backend/.env
   ```

## Log Analysis

### **Understanding Log Messages**

#### **Service Logs**
```bash
# View service logs
sudo journalctl -u dual_recorder.service -f

# Common log patterns:
# ✅ Success messages
# ⚠️ Warning messages  
# ❌ Error messages
# 🔧 Configuration messages
# 📷 Camera-related messages
# 🎬 Recording messages
```

#### **Error Patterns**
```bash
# Find error messages
sudo journalctl -u dual_recorder.service | grep -E "(ERROR|CRITICAL|Exception)"

# Find camera errors
sudo journalctl -u dual_recorder.service | grep -i camera

# Find recording errors
sudo journalctl -u dual_recorder.service | grep -i recording
```

### **Log Analysis Tools**

```bash
# Count error types
sudo journalctl -u dual_recorder.service --since "1 day ago" | grep -c "ERROR"

# Find most common errors
sudo journalctl -u dual_recorder.service --since "1 day ago" | grep "ERROR" | sort | uniq -c | sort -nr

# Monitor logs in real-time
sudo journalctl -u dual_recorder.service -f | grep -E "(ERROR|WARNING)"
```

## Emergency Recovery

### **Complete System Reset**

```bash
# Stop all services
sudo systemctl stop dual_recorder.service
sudo systemctl stop video_worker.service
sudo systemctl stop ezrec-api.service

# Kill all processes
sudo pkill -f dual_recorder
sudo pkill -f video_worker
sudo pkill -f camera
sudo pkill -f libcamera

# Clean up temporary files
sudo rm -rf /tmp/ezrec-*
sudo rm -rf /opt/ezrec-backend/logs/*.log

# Restart services
sudo systemctl start dual_recorder.service
sudo systemctl start video_worker.service
sudo systemctl start ezrec-api.service
```

### **Recovery from Backup**

```bash
# Restore from backup
sudo cp /opt/ezrec-backend/backups/config_*.tar.gz /tmp/
cd /tmp
tar -xzf config_*.tar.gz
sudo cp .env /opt/ezrec-backend/

# Restart services
sudo systemctl restart dual_recorder.service
sudo systemctl restart video_worker.service
sudo systemctl restart ezrec-api.service
```

### **Manual Service Recovery**

```bash
# Start services manually
sudo -u root /opt/ezrec-backend/venv/bin/python3 /opt/ezrec-backend/backend/dual_recorder.py &
sudo -u root /opt/ezrec-backend/venv/bin/python3 /opt/ezrec-backend/backend/video_worker.py &
sudo -u root /opt/ezrec-backend/venv/bin/python3 /opt/ezrec-backend/api/api_server.py &
```

---

**This troubleshooting guide covers the most common issues and their solutions. For additional support, check the system logs and create an issue on GitHub with detailed information.**
