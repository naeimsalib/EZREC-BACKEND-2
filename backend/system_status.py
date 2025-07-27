#!/usr/bin/env python3
"""
EZREC System Status Monitor
- Monitors system health and reports status
- Checks services, disk space, camera availability
- Reports to Supabase for remote monitoring
"""

import os
import sys
import time
import json
import logging
import subprocess
import psutil
import pytz
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# Load environment
load_dotenv("/opt/ezrec-backend/.env", override=True)

# Configuration
TIMEZONE_NAME = os.getenv("TIMEZONE", "UTC")
LOCAL_TZ = pytz.timezone(TIMEZONE_NAME)
LOG_FILE = "/opt/ezrec-backend/logs/system_status.log"
STATUS_FILE = "/opt/ezrec-backend/status.json"

# Required environment variables
REQUIRED_VARS = ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "USER_ID", "CAMERA_ID"]
missing_vars = [var for var in REQUIRED_VARS if not os.getenv(var)]
if missing_vars:
    print(f"❌ Missing required environment variables: {missing_vars}")
    sys.exit(1)

# Optional configuration
STATUS_TABLE = os.getenv("STATUS_TABLE", "cameras")
SUPABASE_RATE_LIMIT_SECONDS = int(os.getenv("SUPABASE_RATE_LIMIT_SECONDS", "300"))  # 5 minutes

# Initialize Supabase client
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("system_status")

class SystemStatusMonitor:
    """Monitor system health and report status"""
    
    def __init__(self):
        self.user_id = os.getenv("USER_ID")
        self.camera_id = os.getenv("CAMERA_ID")
        self.services = [
            "dual_recorder.service",
            "video_worker.service", 
            "ezrec-api.service"
        ]
        
    def check_disk_space(self):
        """Check disk space usage"""
        try:
            disk_usage = psutil.disk_usage('/')
            usage_percent = disk_usage.percent
            free_gb = disk_usage.free / (1024**3)
            
            status = "healthy"
            if usage_percent > 90:
                status = "critical"
            elif usage_percent > 80:
                status = "warning"
            elif usage_percent > 75:
                status = "alert"
                
            return {
                "status": status,
                "usage_percent": usage_percent,
                "free_gb": round(free_gb, 2),
                "total_gb": round(disk_usage.total / (1024**3), 2)
            }
        except Exception as e:
            logger.error(f"❌ Error checking disk space: {e}")
            return {"status": "error", "error": str(e)}
    
    def check_memory_usage(self):
        """Check memory usage"""
        try:
            memory = psutil.virtual_memory()
            return {
                "status": "healthy" if memory.percent < 80 else "warning",
                "usage_percent": memory.percent,
                "available_gb": round(memory.available / (1024**3), 2),
                "total_gb": round(memory.total / (1024**3), 2)
            }
        except Exception as e:
            logger.error(f"❌ Error checking memory: {e}")
            return {"status": "error", "error": str(e)}
    
    def check_cpu_usage(self):
        """Check CPU usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            return {
                "status": "healthy" if cpu_percent < 80 else "warning",
                "usage_percent": cpu_percent
            }
        except Exception as e:
            logger.error(f"❌ Error checking CPU: {e}")
            return {"status": "error", "error": str(e)}
    
    def check_services(self):
        """Check systemd service status (optimized to avoid duplicate subprocess calls)"""
        service_status = {}
        
        for service in self.services:
            try:
                # Use systemctl is-active with proper error handling
                result = subprocess.run(
                    ["systemctl", "is-active", service],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                # Check if the service is actually active
                is_active = result.returncode == 0 and result.stdout.strip() == "active"
                
                # Get more detailed status
                status_result = subprocess.run(
                    ["systemctl", "status", service, "--no-pager"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                service_status[service] = {
                    "active": is_active,
                    "status": result.stdout.strip() if result.returncode == 0 else "inactive",
                    "detailed_status": "running" if is_active else "not running"
                }
                
                # Only get PID for active services (optional optimization)
                if is_active and os.getenv("INCLUDE_SERVICE_PIDS", "false").lower() == "true":
                    try:
                        status_result = subprocess.run(
                            ["systemctl", "status", service, "--no-pager"],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        if status_result.returncode == 0:
                            lines = status_result.stdout.split('\n')
                            for line in lines:
                                if 'Main PID:' in line:
                                    service_status[service]["pid"] = line.split()[-1]
                                    break
                    except Exception:
                        pass
                        
            except Exception as e:
                logger.error(f"❌ Error checking service {service}: {e}")
                service_status[service] = {
                    "active": False,
                    "status": "error",
                    "error": str(e)
                }
        
        return service_status
    
    def check_camera_availability(self):
        """Check if cameras are available"""
        try:
            # Try to import picamera2
            try:
                from picamera2 import Picamera2
                picamera2_available = True
            except ImportError:
                picamera2_available = False
                logger.warning("⚠️ Picamera2 not available")
            
            if not picamera2_available:
                return {
                    "status": "error",
                    "available": False,
                    "error": "Picamera2 not available"
                }
            
            # Try to detect cameras
            available_cameras = []
            for i in range(4):  # Check up to 4 camera indices
                try:
                    camera = Picamera2(index=i)
                    props = camera.camera_properties
                    serial = props.get('SerialNumber', f'unknown_{i}')
                    available_cameras.append({
                        "index": i,
                        "serial": serial
                    })
                    camera.close()
                except Exception:
                    continue
            
            return {
                "status": "healthy" if len(available_cameras) >= 2 else "warning",
                "available": True,
                "camera_count": len(available_cameras),
                "cameras": available_cameras
            }
            
        except Exception as e:
            logger.error(f"❌ Error checking camera availability: {e}")
            return {
                "status": "error",
                "available": False,
                "error": str(e)
            }
    
    def check_api_health(self):
        """Check if the API is responding"""
        try:
            import requests
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                return {
                    "status": "healthy",
                    "responding": True,
                    "api_status": health_data.get("status", "unknown"),
                    "warnings": health_data.get("warnings", [])
                }
            else:
                return {
                    "status": "warning",
                    "responding": True,
                    "api_status": f"http_{response.status_code}"
                }
        except Exception as e:
            logger.error(f"❌ Error checking API health: {e}")
            return {
                "status": "error",
                "responding": False,
                "error": str(e)
            }
    
    def check_ffmpeg(self):
        """Check if FFmpeg is available"""
        try:
            # Use shutil.which to find ffmpeg and ffprobe with fallbacks
            import shutil
            
            ffmpeg_path = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
            ffprobe_path = shutil.which("ffprobe") or "/usr/bin/ffprobe"
            
            # Verify ffmpeg works
            result = subprocess.run(
                [ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Extract version from output
                version_line = result.stdout.split('\n')[0]
                version = version_line.split()[2] if len(version_line.split()) > 2 else "unknown"
                
                return {
                    "status": "healthy",
                    "available": True,
                    "version": version
                }
            else:
                return {
                    "status": "error",
                    "available": False,
                    "error": "FFmpeg not found or not working"
                }
        except Exception as e:
            logger.error(f"❌ Error checking FFmpeg: {e}")
            return {
                "status": "error",
                "available": False,
                "error": str(e)
            }
    
    def check_environment_variables(self):
        """Check if all required environment variables are set"""
        required_vars = [
            "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "USER_ID", "CAMERA_ID",
            "AWS_REGION", "AWS_S3_BUCKET", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        return {
            "status": "healthy" if not missing_vars else "error",
            "all_set": len(missing_vars) == 0,
            "missing_vars": missing_vars
        }
    
    def check_recording_status(self):
        """Check if system is currently recording"""
        try:
            status_file = Path(STATUS_FILE)
            if status_file.exists():
                with open(status_file) as f:
                    status_data = json.load(f)
                is_recording = status_data.get("is_recording", False)
            else:
                is_recording = False
            
            return {
                "status": "recording" if is_recording else "idle",
                "is_recording": is_recording
            }
        except Exception as e:
            logger.error(f"❌ Error checking recording status: {e}")
            return {
                "status": "error",
                "is_recording": False,
                "error": str(e)
            }
    
    def get_system_info(self):
        """Get basic system information"""
        try:
            # Get hostname
            hostname = subprocess.run(
                ["hostname"],
                capture_output=True,
                text=True,
                timeout=5
            ).stdout.strip()
            
            # Get uptime
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_hours = uptime_seconds / 3600
            
            return {
                "hostname": hostname,
                "uptime_hours": round(uptime_hours, 2),
                "timezone": TIMEZONE_NAME,
                "timestamp": datetime.now(LOCAL_TZ).isoformat()
            }
        except Exception as e:
            logger.error(f"❌ Error getting system info: {e}")
            return {"error": str(e)}
    
    def generate_health_report(self):
        """Generate comprehensive health report"""
        logger.info("🔍 Generating system health report...")
        
        report = {
            "system_info": self.get_system_info(),
            "disk_space": self.check_disk_space(),
            "memory_usage": self.check_memory_usage(),
            "cpu_usage": self.check_cpu_usage(),
            "services": self.check_services(),
            "camera_availability": self.check_camera_availability(),
            "api_health": self.check_api_health(),
            "ffmpeg": self.check_ffmpeg(),
            "environment": self.check_environment_variables(),
            "recording_status": self.check_recording_status()
        }
        
        # Determine overall system status
        critical_issues = []
        warnings = []
        
        # Check for critical issues
        if report["disk_space"]["status"] == "critical":
            critical_issues.append("Disk space critical")
        elif report["disk_space"]["status"] == "warning":
            warnings.append("Disk space warning")
        
        if report["memory_usage"]["status"] == "warning":
            warnings.append("High memory usage")
        
        if report["cpu_usage"]["status"] == "warning":
            warnings.append("High CPU usage")
        
        # Check services
        inactive_services = []
        for service_name, service_status in report["services"].items():
            if not service_status.get("active", False):
                inactive_services.append(service_name)
        
        if inactive_services:
            critical_issues.append(f"Inactive services: {', '.join(inactive_services)}")
        
        # Check camera availability
        if report["camera_availability"]["status"] == "error":
            critical_issues.append("Camera system error")
        elif report["camera_availability"]["status"] == "warning":
            warnings.append("Insufficient cameras")
        
        # Check API health
        if report["api_health"]["status"] == "error":
            critical_issues.append("API not responding")
        
        # Check FFmpeg
        if report["ffmpeg"]["status"] == "error":
            critical_issues.append("FFmpeg not available")
        
        # Check environment
        if report["environment"]["status"] == "error":
            critical_issues.append("Missing environment variables")
        
        # Set overall status
        if critical_issues:
            report["overall_status"] = "critical"
        elif warnings:
            report["overall_status"] = "warning"
        else:
            report["overall_status"] = "healthy"
        
        report["critical_issues"] = critical_issues
        report["warnings"] = warnings
        
        return report
    
    def save_status_locally(self, report):
        """Save status report to local file"""
        try:
            status_file = Path(STATUS_FILE)
            status_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(status_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"✅ Status saved to {status_file}")
        except Exception as e:
            logger.error(f"❌ Error saving status locally: {e}")
    
    def update_supabase_status(self, report):
        """Update status in Supabase with rate limiting"""
        try:
            # Check if we should update (rate limiting)
            last_update_file = Path("/tmp/ezrec_status_last_update")
            current_time = time.time()
            
            if last_update_file.exists():
                try:
                    last_update = float(last_update_file.read_text().strip())
                    if current_time - last_update < SUPABASE_RATE_LIMIT_SECONDS:
                        logger.debug("⏳ Rate limiting: skipping Supabase update")
                        return
                except (ValueError, IOError):
                    pass
            
            # Update camera status in Supabase (only basic fields that exist)
            update_data = {
                'status': report["overall_status"],
                'last_seen': datetime.now(LOCAL_TZ).isoformat(),
            }
            
            # Try to add additional fields one by one to avoid schema issues
            optional_fields = [
                ('system_info', json.dumps(report["system_info"])),
                ('disk_usage', report["disk_space"]["usage_percent"]),
                ('memory_usage', report["memory_usage"]["usage_percent"]),
                ('cpu_usage', report["cpu_usage"]["usage_percent"]),
                ('camera_count', report["camera_availability"].get("camera_count", 0)),
            ]
            
            for field_name, field_value in optional_fields:
                try:
                    update_data[field_name] = field_value
                except Exception as e:
                    logger.debug(f"Field {field_name} not available in database: {e}")
            
            try:
                supabase.table(STATUS_TABLE).update(update_data).eq('id', self.camera_id).execute()
            except Exception as e:
                logger.error(f"❌ Failed to update Supabase: {e}")
                # Try with just the basic fields
                try:
                    basic_data = {
                        'status': report["overall_status"],
                        'last_seen': datetime.now(LOCAL_TZ).isoformat(),
                    }
                    supabase.table(STATUS_TABLE).update(basic_data).eq('id', self.camera_id).execute()
                    logger.info("✅ Updated Supabase with basic fields only")
                except Exception as e2:
                    logger.error(f"❌ Failed to update Supabase even with basic fields: {e2}")
            
            # Update last update timestamp
            last_update_file.write_text(str(current_time))
            logger.info(f"📡 Status updated in Supabase for camera {self.camera_id}")
        except Exception as e:
            logger.error(f"❌ Error updating Supabase status: {e}")
    
    def run_health_check(self):
        """Run complete health check and report"""
        logger.info("🏥 Starting system health check...")
        
        try:
            # Generate health report
            report = self.generate_health_report()
            
            # Log summary
            logger.info(f"📊 Overall Status: {report['overall_status'].upper()}")
            if report["critical_issues"]:
                logger.error(f"🚨 Critical Issues: {', '.join(report['critical_issues'])}")
            if report["warnings"]:
                logger.warning(f"⚠️ Warnings: {', '.join(report['warnings'])}")
            
            # Save locally
            self.save_status_locally(report)
            
            # Update Supabase
            self.update_supabase_status(report)
            
            logger.info("✅ Health check completed successfully")
            return report
            
        except Exception as e:
            logger.error(f"❌ Error during health check: {e}")
            return None

def main():
    """Main function"""
    logger.info("🚀 System Status Monitor starting...")
    
    try:
        monitor = SystemStatusMonitor()
        
        # Run initial health check
        report = monitor.run_health_check()
        
        if report:
            logger.info(f"✅ System Status: {report['overall_status']}")
        else:
            logger.error("❌ Failed to generate health report")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Fatal error in system status monitor: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 