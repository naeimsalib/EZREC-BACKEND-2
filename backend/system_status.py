#!/usr/bin/env python3
"""
EZREC System Status Monitor
Monitors system health and reports status to Supabase
"""

import os
import sys
import time
import json
import logging
import subprocess
import psutil
import pytz
import shutil
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Find systemctl path
SYSTEMCTL = shutil.which("systemctl") or "/bin/systemctl"

# Monkey patch Picamera2 to fix _preview attribute error
try:
    from picamera2 import Picamera2
    
    # Store the original close method
    original_close = Picamera2.close
    
    def safe_close(self):
        """Safe close method that handles missing _preview attribute"""
        try:
            if hasattr(self, '_preview'):
                return original_close(self)
            else:
                # If _preview doesn't exist, just clean up what we can
                if hasattr(self, '_camera'):
                    self._camera = None
                if hasattr(self, '_encoder'):
                    self._encoder = None
        except Exception as e:
            # Silently ignore errors during cleanup
            pass
    
    # Replace the close method
    Picamera2.close = safe_close
    
    # Also patch the __del__ method to be safer
    original_del = Picamera2.__del__
    
    def safe_del(self):
        """Safe destructor that handles missing attributes"""
        try:
            if hasattr(self, '_preview'):
                return original_del(self)
        except Exception:
            # Silently ignore errors during destruction
            pass
    
    Picamera2.__del__ = safe_del
    
except ImportError:
    pass  # Picamera2 not available, continue without it

# Load environment variables
dotenv_path = "/opt/ezrec-backend/.env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print(f"❌ .env file not found at {dotenv_path}")
    sys.exit(1)

# Configuration
TIMEZONE_NAME = os.getenv("LOCAL_TIMEZONE", "UTC")
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
        """Check if all required services are running"""
        services = [
            "dual_recorder.service",
            "video_worker.service", 
            "ezrec-api.service"
        ]
        
        service_status = {}
        inactive_services = []
        
        for service in services:
            try:
                result = subprocess.run(
                    [SYSTEMCTL, "is-active", service],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                is_active = result.returncode == 0
                service_status[service] = {
                    "active": is_active,
                    "status": result.stdout.strip() if is_active else result.stderr.strip()
                }
                
                if not is_active:
                    inactive_services.append(service)
                    
            except Exception as e:
                logger.error(f"❌ Error checking service {service}: {e}")
                service_status[service] = {
                    "active": False,
                    "error": str(e)
                }
                inactive_services.append(service)
        
        # Check if system_status.timer is active
        try:
            result = subprocess.run([SYSTEMCTL, 'is-active', 'system_status.timer'],
                                  capture_output=True, text=True, timeout=5)
            timer_active = result.returncode == 0
        except Exception as e:
            logger.error(f"❌ Error checking system_status.timer: {e}")
            timer_active = False
            
        return {
            "services": service_status,
            "inactive": inactive_services,
            "timer_active": timer_active
        }
    
    def is_capture_device(self, device_path):
        """Check if a video device supports capture"""
        try:
            result = subprocess.run(
                ['v4l2-ctl', '--device', device_path, '--all'],
                capture_output=True, text=True, timeout=5
            )
            return 'Video Capture' in result.stdout
        except Exception:
            return False
    
    def check_camera_availability(self):
        """Check if cameras are available"""
        # First, try Picamera2
        try:
            from picamera2 import Picamera2
            available = []
            
            # Try to create a Picamera2 instance (auto-detects first camera)
            try:
                cam = Picamera2()  # Removed index=i
                serial = cam.camera_properties.get("SerialNumber", "unknown_0")
                available.append(serial)
                cam.close()
                
                # For dual camera setup, we'll use the same camera twice for testing
                available.append(serial)  # Add same camera twice for dual setup
                
            except Exception as e:
                logger.debug(f"Camera not available: {e}")
            
            cam_count = len(available)
        except ImportError:
            cam_count = 0

        # If Picamera2 sees <2 cameras, fallback to v4l2-ctl listing
        if cam_count < 2:
            physical_cameras = self.list_physical_cameras()
            cam_count = len(physical_cameras)

        status = "healthy" if cam_count >= 2 else "warning"
        return {
            "status": status,
            "available": cam_count > 0,
            "camera_count": cam_count
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
        try:
            # Check system resources
            disk_usage = self.check_disk_space()
            memory_usage = self.check_memory_usage()
            cpu_usage = self.check_cpu_usage()
            
            # Check services
            service_status = self.check_services()
            
            # Check cameras
            camera_status = self.check_camera_availability()
            
            # Check FFmpeg
            ffmpeg_status = self.check_ffmpeg()
            
            # Check environment variables
            env_status = self.check_environment_variables()
            
            # Check recording status
            recording_status = self.check_recording_status()
            
            # Determine overall status
            critical_issues = []
            warnings = []
            
            # Check for critical issues
            if disk_usage["usage_percent"] > 90:
                critical_issues.append(f"High disk usage: {disk_usage['usage_percent']:.1f}%")
            
            if memory_usage["usage_percent"] > 90:
                critical_issues.append(f"High memory usage: {memory_usage['usage_percent']:.1f}%")
            
            if not ffmpeg_status["available"]:
                critical_issues.append("FFmpeg not available")
            
            if not env_status["all_set"]:
                critical_issues.append(f"Missing environment variables: {env_status['missing_vars']}")
            
            # Check for inactive services (excluding system_status.service as it's one-shot)
            inactive = service_status["inactive"]
            if inactive:
                critical_issues.append(f"Inactive services: {', '.join(inactive)}")
            
            # Check camera warnings
            if camera_status["camera_count"] < 2:
                warnings.append("Insufficient cameras")
            
            # Determine overall status
            if critical_issues:
                overall_status = "critical"
            elif warnings:
                overall_status = "warning"
            else:
                overall_status = "healthy"
            
            return {
                "timestamp": datetime.now().isoformat(),
                "overall_status": overall_status,
                "critical_issues": critical_issues,
                "warnings": warnings,
                "disk_usage": disk_usage,
                "memory_usage": memory_usage,
                "cpu_usage": cpu_usage,
                "services": service_status,
                "cameras": camera_status,
                "ffmpeg": ffmpeg_status,
                "environment": env_status,
                "recording": recording_status
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating health report: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "overall_status": "error",
                "error": str(e)
            }
    
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
        """Update camera status in Supabase"""
        try:
            # Rate-limit Supabase updates
            import time
            last_update_file = Path("/tmp/ezrec_status_last_update")
            current_time = time.time()
            
            # Only update if more than 30 seconds have passed
            if last_update_file.exists():
                last_update = float(last_update_file.read_text().strip())
                if current_time - last_update < 30:
                    return
                    
            # Update the last update time
            last_update_file.write_text(str(current_time))
            
            # Get camera ID from environment
            camera_id = os.getenv("CAMERA_ID")
            if not camera_id:
                logger.warning("⚠️ CAMERA_ID not found in environment")
                return
                
            # Use only guaranteed columns to avoid schema mismatches
            basic_data = {
                "status": report["overall_status"]
            }
            
            # Update Supabase using the global client with better error handling
            try:
                response = supabase.table("cameras").update(basic_data).eq("id", camera_id).execute()
                
                if hasattr(response, 'data') and response.data:
                    logger.info("✅ Camera status updated in Supabase")
                else:
                    logger.warning("⚠️ No data returned from Supabase update")
                    
            except Exception as supabase_error:
                logger.error(f"❌ Supabase connection error: {supabase_error}")
                # Don't fail the entire health check due to Supabase issues
                return
                
        except Exception as e:
            logger.error(f"❌ Error updating Supabase status: {e}")
            # Don't fail the entire health check due to Supabase issues
    
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

    def list_physical_cameras(self):
        """Get list of physical camera devices using v4l2-ctl"""
        try:
            result = subprocess.run(
                ["v4l2-ctl", "--list-devices"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                return []
                
            cameras = []
            lines = result.stdout.splitlines()
            for i, line in enumerate(lines):
                if line.endswith(":"):
                    # Next lines that start with a tab are nodes
                    j = i + 1
                    while j < len(lines) and lines[j].startswith("\t"):
                        node = lines[j].strip().split()[0]
                        if node.startswith("/dev/video"):
                            cameras.append(node)
                        j += 1
            return cameras
        except Exception as e:
            logger.error(f"❌ Error listing physical cameras: {e}")
            return []

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