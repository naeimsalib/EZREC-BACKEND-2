# EZREC Complete Setup Guide

**Comprehensive step-by-step guide for setting up the EZREC dual-camera recording system**

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Hardware Setup](#hardware-setup)
- [Software Installation](#software-installation)
- [Configuration](#configuration)
- [Testing](#testing)
- [Production Deployment](#production-deployment)
- [Maintenance](#maintenance)

## Prerequisites

### **Hardware Requirements**

- **Raspberry Pi 4/5** (4GB RAM minimum, 8GB recommended)
- **Two compatible cameras**:
  - IMX477 (High Quality Camera Module)
  - IMX219 (Camera Module v2)
  - Any V4L2 compatible camera
- **MicroSD card** (32GB+ Class 10, 64GB+ recommended)
- **Power supply** (5V 3A minimum)
- **Network connection** (Ethernet or WiFi)

### **Software Requirements**

- **Raspberry Pi OS** (64-bit recommended)
- **Python 3.11+**
- **Git**
- **FFmpeg**
- **v4l2-utils**

### **External Services**

- **Supabase account** (for database and authentication)
- **AWS account** (for S3 storage)
- **Domain name** (optional, for external access)

## Hardware Setup

### **1. Camera Installation**

1. **Connect Cameras to CSI Ports**
   ```
   Camera 1 → CSI0 (closest to power/USB)
   Camera 2 → CSI1 (farthest from power/USB)
   ```

2. **Enable Camera Interface**
   ```bash
   sudo raspi-config
   # Navigate to: Interface Options > Camera > Enable
   # Reboot when prompted
   ```

3. **Verify Camera Detection**
   ```bash
   # Check camera devices
   v4l2-ctl --list-devices
   
   # Expected output:
   # bcm2835-codec-decode (platform:bcm2835-codec):
   #     /dev/video10
   #     /dev/video11
   #     /dev/video12
   # imx477 10-001a (platform:fe801000.csi):
   #     /dev/video0
   #     /dev/video1
   #     /dev/video2
   #     /dev/video3
   # imx477 11-001a (platform:fe801000.csi):
   #     /dev/video4
   #     /dev/video5
   #     /dev/video6
   #     /dev/video7
   ```

### **2. Storage Setup**

1. **Check Available Storage**
   ```bash
   df -h
   # Ensure at least 10GB free space
   ```

2. **Create Recording Directory**
   ```bash
   sudo mkdir -p /opt/ezrec-backend/recordings
   sudo chown -R $USER:$USER /opt/ezrec-backend
   ```

### **3. Network Configuration**

1. **Configure Static IP (Recommended)**
   ```bash
   sudo nano /etc/dhcpcd.conf
   
   # Add at the end:
   interface eth0
   static ip_address=192.168.1.100/24
   static routers=192.168.1.1
   static domain_name_servers=8.8.8.8 8.8.4.4
   ```

2. **Test Network Connectivity**
   ```bash
   ping google.com
   ping github.com
   ```

## Software Installation

### **1. System Update**

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y git curl wget vim htop
```

### **2. Install Dependencies**

```bash
# Install FFmpeg and video tools
sudo apt install -y ffmpeg v4l-utils

# Install Python development tools
sudo apt install -y python3-pip python3-venv python3-dev

# Install system dependencies
sudo apt install -y libcamera-tools libcamera-dev
```

### **3. Clone Repository**

```bash
# Clone the EZREC repository
git clone https://github.com/naeimsalib/EZREC-BACKEND-2.git
cd EZREC-BACKEND-2

# Verify repository structure
ls -la
```

### **4. Run Deployment Script**

```bash
# Make deployment script executable
chmod +x deployment.sh

# Run comprehensive deployment
sudo ./deployment.sh
```

The deployment script will:
- Install all Python dependencies
- Create virtual environments
- Set up systemd services
- Configure file permissions
- Test system functionality

## Configuration

### **1. Environment Variables**

1. **Create Environment File**
   ```bash
   sudo cp env.example /opt/ezrec-backend/.env
   sudo nano /opt/ezrec-backend/.env
   ```

2. **Configure Required Variables**
   ```bash
   # Supabase Configuration
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
   
   # AWS S3 Configuration
   AWS_ACCESS_KEY_ID=your_access_key_here
   AWS_SECRET_ACCESS_KEY=your_secret_key_here
   AWS_DEFAULT_REGION=us-east-1
   S3_BUCKET=your-bucket-name
   
   # User Configuration
   USER_ID=your-user-id
   CAMERA_ID=your-camera-id
   
   # Optional: Email Configuration
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password
   EMAIL_USE_TLS=True
   EMAIL_FROM=your-email@gmail.com
   ```

### **2. Supabase Setup**

1. **Create Supabase Project**
   - Go to [supabase.com](https://supabase.com)
   - Create new project
   - Note the URL and service role key

2. **Create Database Tables**
   ```sql
   -- Create bookings table
   CREATE TABLE bookings (
     id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
     user_id TEXT NOT NULL,
     camera_id TEXT NOT NULL,
     start_time TIMESTAMPTZ NOT NULL,
     end_time TIMESTAMPTZ NOT NULL,
     status TEXT DEFAULT 'scheduled',
     created_at TIMESTAMPTZ DEFAULT NOW(),
     updated_at TIMESTAMPTZ DEFAULT NOW()
   );
   
   -- Create recordings table
   CREATE TABLE recordings (
     id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
     booking_id UUID REFERENCES bookings(id),
     file_path TEXT NOT NULL,
     file_size BIGINT,
     duration INTEGER,
     status TEXT DEFAULT 'processing',
     created_at TIMESTAMPTZ DEFAULT NOW()
   );
   ```

### **3. AWS S3 Setup**

1. **Create S3 Bucket**
   - Go to AWS S3 Console
   - Create new bucket
   - Configure CORS policy:
   ```json
   [
     {
       "AllowedHeaders": ["*"],
       "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
       "AllowedOrigins": ["*"],
       "ExposeHeaders": []
     }
   ]
   ```

2. **Create IAM User**
   - Create IAM user with S3 access
   - Attach policy:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:GetObject",
           "s3:PutObject",
           "s3:DeleteObject",
           "s3:ListBucket"
         ],
         "Resource": [
           "arn:aws:s3:::your-bucket-name",
           "arn:aws:s3:::your-bucket-name/*"
         ]
       }
     ]
   }
   ```

### **4. Service Configuration**

1. **Verify Service Status**
   ```bash
   sudo systemctl status dual_recorder.service
   sudo systemctl status video_worker.service
   sudo systemctl status ezrec-api.service
   ```

2. **Enable Auto-Start**
   ```bash
   sudo systemctl enable dual_recorder.service
   sudo systemctl enable video_worker.service
   sudo systemctl enable ezrec-api.service
   ```

## Testing

### **1. System Health Check**

```bash
# Run comprehensive system test
sudo python3 test.py
```

Expected output:
```
🧪 EZREC Complete System Test
==================================================

1️⃣ Testing camera detection...
✅ Camera 0 detected
✅ Camera 1 detected
📷 Available cameras: [0, 1]

2️⃣ Testing simple recording...
✅ Camera started successfully
✅ Recording started
✅ Recording stopped
✅ Camera closed
✅ Recording file created: 1234567 bytes

3️⃣ Creating test booking...
✅ Test booking created:
   ID: test-booking-1234567890
   Start: 2025-01-14 10:30:00-05:00
   End: 2025-01-14 10:32:00-05:00
   Duration: 2 minutes

4️⃣ Testing service recording...
✅ dual_recorder service is active
✅ Service logs look clean

5️⃣ Checking recording files...
✅ Found 2 recording files:
   📄 camera_0.mp4: 1234567 bytes
   📄 camera_1.mp4: 1234567 bytes

==================================================
📊 TEST RESULTS SUMMARY:
==================================================
Camera Detection: ✅ PASS
Simple Recording: ✅ PASS
Booking Creation: ✅ PASS
Service Recording: ✅ PASS
Recording Files: ✅ PASS

🎉 ALL TESTS PASSED! System is working correctly.
```

### **2. API Testing**

```bash
# Test API health endpoint
curl http://localhost:8000/health

# Expected response:
{
  "success": true,
  "data": {
    "status": "healthy",
    "services": {
      "dual_recorder": "running",
      "video_worker": "running",
      "api_server": "running"
    },
    "cameras": 2,
    "disk_space": "85%",
    "timestamp": "2025-01-14T10:30:00Z"
  }
}
```

### **3. Recording Test**

```bash
# Create test booking
python3 -c "
import json
import datetime
import pytz

now = datetime.datetime.now(pytz.timezone('America/New_York'))
start_time = now.isoformat()
end_time = (now + datetime.timedelta(minutes=2)).isoformat()

booking = {
    'id': 'test-recording-$(date +%s)',
    'start_time': start_time,
    'end_time': end_time,
    'title': 'Test Recording',
    'description': 'Testing the recording system'
}

with open('/opt/ezrec-backend/api/local_data/bookings.json', 'w') as f:
    json.dump([booking], f, indent=2)

print(f'✅ Created test booking: {booking[\"id\"]}')
"

# Monitor recording
sudo journalctl -u dual_recorder.service -f
```

## Production Deployment

### **1. Security Hardening**

1. **Change Default Passwords**
   ```bash
   sudo passwd pi
   sudo passwd root
   ```

2. **Configure Firewall**
   ```bash
   sudo ufw enable
   sudo ufw allow ssh
   sudo ufw allow 8000/tcp
   sudo ufw allow 22/tcp
   ```

3. **Disable Unnecessary Services**
   ```bash
   sudo systemctl disable bluetooth
   sudo systemctl disable cups
   sudo systemctl disable cups-browsed
   ```

### **2. SSL/TLS Configuration**

1. **Install Certbot**
   ```bash
   sudo apt install certbot python3-certbot-nginx
   ```

2. **Obtain SSL Certificate**
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```

### **3. Monitoring Setup**

1. **Install Monitoring Tools**
   ```bash
   sudo apt install htop iotop nethogs
   ```

2. **Set Up Log Rotation**
   ```bash
   sudo nano /etc/logrotate.d/ezrec
   
   # Add:
   /opt/ezrec-backend/logs/*.log {
       daily
       missingok
       rotate 7
       compress
       delaycompress
       notifempty
       create 644 root root
   }
   ```

### **4. Backup Configuration**

1. **Create Backup Script**
   ```bash
   sudo nano /opt/ezrec-backend/backup.sh
   
   # Add:
   #!/bin/bash
   BACKUP_DIR="/opt/ezrec-backend/backups"
   DATE=$(date +%Y%m%d_%H%M%S)
   
   mkdir -p $BACKUP_DIR
   
   # Backup configuration
   tar -czf $BACKUP_DIR/config_$DATE.tar.gz /opt/ezrec-backend/.env
   
   # Backup recordings (last 7 days)
   find /opt/ezrec-backend/recordings -name "*.mp4" -mtime -7 -exec tar -czf $BACKUP_DIR/recordings_$DATE.tar.gz {} +
   
   # Cleanup old backups (keep 30 days)
   find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
   ```

2. **Schedule Backup**
   ```bash
   sudo chmod +x /opt/ezrec-backend/backup.sh
   sudo crontab -e
   
   # Add:
   0 2 * * * /opt/ezrec-backend/backup.sh
   ```

## Maintenance

### **1. Regular Maintenance Tasks**

1. **System Updates**
   ```bash
   # Weekly system updates
   sudo apt update && sudo apt upgrade -y
   ```

2. **Log Cleanup**
   ```bash
   # Clean old logs
   sudo find /opt/ezrec-backend/logs -name "*.log" -mtime +30 -delete
   ```

3. **Recording Cleanup**
   ```bash
   # Clean old recordings (older than 30 days)
   sudo find /opt/ezrec-backend/recordings -name "*.mp4" -mtime +30 -delete
   ```

### **2. Health Monitoring**

1. **Daily Health Check**
   ```bash
   # Add to crontab
   0 6 * * * /usr/bin/python3 /opt/ezrec-backend/test.py >> /opt/ezrec-backend/logs/health_check.log 2>&1
   ```

2. **Service Monitoring**
   ```bash
   # Check service status
   sudo systemctl status dual_recorder.service video_worker.service ezrec-api.service
   ```

### **3. Performance Optimization**

1. **Monitor Resource Usage**
   ```bash
   # Check CPU and memory usage
   htop
   
   # Check disk usage
   df -h
   
   # Check network usage
   iftop
   ```

2. **Optimize Recording Quality**
   ```bash
   # Edit camera settings in config/settings.py
   sudo nano /opt/ezrec-backend/config/settings.py
   ```

### **4. Troubleshooting**

1. **Common Issues**
   - Camera not detected: Check connections and enable camera interface
   - Service not starting: Check logs with `journalctl -u service-name`
   - Recording failures: Check disk space and permissions
   - Upload issues: Verify AWS credentials and network connectivity

2. **Log Analysis**
   ```bash
   # View recent errors
   sudo journalctl -u dual_recorder.service --since "1 hour ago" | grep ERROR
   
   # Monitor real-time logs
   sudo journalctl -u dual_recorder.service -f
   ```

## Support

For additional support:
- Check the troubleshooting section in the main README
- Review system logs for error messages
- Create an issue on GitHub with detailed information
- Include system information and error logs when reporting issues

---

**This setup guide provides comprehensive instructions for deploying EZREC in production environments. Follow each step carefully to ensure a successful deployment.**
