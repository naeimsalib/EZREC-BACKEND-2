#!/usr/bin/env python3
"""
EZREC Complete System Test Suite
Comprehensive testing of the entire EZREC dual-camera recording system
Tests all components: cameras, recording, services, API, and integrations
"""

import os
import sys
import time
import json
import logging
import subprocess
import requests
from pathlib import Path
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Optional, Tuple

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EZRECSystemTester:
    """Comprehensive EZREC system tester"""
    
    def __init__(self):
        self.results = {}
        self.test_start_time = datetime.now()
        self.api_base_url = "http://localhost:8000"
        self.recordings_dir = Path("/opt/ezrec-backend/recordings")
        self.backend_dir = Path("/opt/ezrec-backend/backend")
        self.logs_dir = Path("/opt/ezrec-backend/logs")
        
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.results[test_name] = success
        return success
    
    def run_command(self, command: List[str], timeout: int = 30) -> Tuple[bool, str, str]:
        """Run a system command and return success, stdout, stderr"""
        try:
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)
    
    def test_system_services(self) -> bool:
        """Test 1: Check all systemd services are running"""
        print("\n🔧 Testing System Services...")
        
        services = [
            "dual_recorder.service",
            "video_worker.service", 
            "ezrec-api.service",
            "system_status.service",
            "cloudflared.service"
        ]
        
        all_running = True
        for service in services:
            success, stdout, stderr = self.run_command(["systemctl", "is-active", service])
            if success and stdout.strip() == "active":
                self.log_test(f"Service: {service}", True, "Running")
            else:
                self.log_test(f"Service: {service}", False, f"Not running: {stderr}")
                all_running = False
        
        return self.log_test("All Services Running", all_running)
    
    def test_camera_detection(self) -> bool:
        """Test 2: Detect and test camera availability"""
        print("\n📷 Testing Camera Detection...")
        
        # Test camera devices exist
        camera_devices = ["/dev/video0", "/dev/video1"]
        available_cameras = []
        
        for device in camera_devices:
            if os.path.exists(device):
                self.log_test(f"Camera Device: {device}", True, "Exists")
                available_cameras.append(device)
            else:
                self.log_test(f"Camera Device: {device}", False, "Not found")
        
        if not available_cameras:
            return self.log_test("Camera Detection", False, "No cameras found")
        
        # Test rpicam-vid detection
        success, stdout, stderr = self.run_command(["rpicam-vid", "--list-cameras"])
        if success or "Available cameras" in stderr or "imx477" in stderr:
            self.log_test("rpicam-vid Detection", True, "Cameras detected")
        else:
            self.log_test("rpicam-vid Detection", False, f"Error: {stderr}")
        
        # Test camera permissions
        for device in available_cameras:
            try:
                with open(device, 'rb') as f:
                    f.read(1)
                self.log_test(f"Camera Access: {device}", True, "Readable")
            except Exception as e:
                self.log_test(f"Camera Access: {device}", False, f"Access denied: {e}")
        
        return self.log_test("Camera Detection", len(available_cameras) > 0)
    
    def test_api_endpoints(self) -> bool:
        """Test 3: Test API endpoints"""
        print("\n🌐 Testing API Endpoints...")
        
        endpoints = [
            ("/test-alive", "GET"),
            ("/status", "GET"),
            ("/api/bookings", "GET"),
            ("/api/cameras", "GET"),
            ("/api/recordings", "GET")
        ]
        
        all_working = True
        for endpoint, method in endpoints:
            try:
                url = f"{self.api_base_url}{endpoint}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    self.log_test(f"API: {endpoint}", True, f"Status {response.status_code}")
                else:
                    self.log_test(f"API: {endpoint}", False, f"Status {response.status_code}")
                    all_working = False
                    
            except Exception as e:
                self.log_test(f"API: {endpoint}", False, f"Error: {e}")
                all_working = False
        
        return self.log_test("API Endpoints", all_working)
    
    def test_environment_configuration(self) -> bool:
        """Test 4: Check environment configuration"""
        print("\n⚙️ Testing Environment Configuration...")
        
        # Check .env file exists
        env_file = Path("/opt/ezrec-backend/.env")
        if env_file.exists():
            self.log_test("Environment File", True, "Found")
            
            # Check required variables
            required_vars = [
                "USER_ID", "CAMERA_ID", "SUPABASE_URL", 
                "SUPABASE_SERVICE_ROLE_KEY", "LOCAL_TIMEZONE"
            ]
            
            with open(env_file, 'r') as f:
                env_content = f.read()
            
            missing_vars = []
            for var in required_vars:
                if f"{var}=" in env_content:
                    self.log_test(f"Env Var: {var}", True, "Set")
                else:
                    self.log_test(f"Env Var: {var}", False, "Missing")
                    missing_vars.append(var)
            
            return self.log_test("Environment Config", len(missing_vars) == 0)
        else:
            return self.log_test("Environment Config", False, "No .env file found")
    
    def test_booking_system(self) -> bool:
        """Test 5: Test booking system functionality"""
        print("\n📅 Testing Booking System...")
        
        # Check booking cache file
        booking_cache = self.backend_dir / "bookings.json"
        if booking_cache.exists():
            try:
                with open(booking_cache, 'r') as f:
                    bookings_data = json.load(f)
                self.log_test("Booking Cache File", True, f"Contains {len(bookings_data.get('bookings', []))} bookings")
            except Exception as e:
                self.log_test("Booking Cache File", False, f"Invalid JSON: {e}")
                return False
        else:
            self.log_test("Booking Cache File", False, "File not found")
            return False
        
        # Test creating a booking via API
        try:
            now = datetime.now(pytz.timezone('America/New_York'))
            start_time = now + timedelta(minutes=1)
            end_time = start_time + timedelta(minutes=2)
            
            booking_data = {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "title": "System Test Booking",
                "description": "Automated test booking"
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/bookings",
                json=booking_data,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                self.log_test("Booking Creation", True, "API accepted booking")
                return True
            else:
                self.log_test("Booking Creation", False, f"API error: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Booking Creation", False, f"Error: {e}")
            return False
    
    def test_recording_functionality(self) -> bool:
        """Test 6: Test recording functionality"""
        print("\n🎬 Testing Recording Functionality...")
        
        # Check recordings directory structure
        if not self.recordings_dir.exists():
            self.log_test("Recordings Directory", False, "Directory not found")
            return False
        
        self.log_test("Recordings Directory", True, "Exists")
        
        # Check today's recording directory
        today = datetime.now().strftime("%Y-%m-%d")
        today_dir = self.recordings_dir / today
        
        if not today_dir.exists():
            # Create it for testing
            today_dir.mkdir(parents=True, exist_ok=True)
            self.log_test("Today's Recording Dir", True, "Created")
        else:
            self.log_test("Today's Recording Dir", True, "Exists")
        
        # Check for existing recordings
        mp4_files = list(today_dir.glob("*.mp4"))
        if mp4_files:
            self.log_test("Existing Recordings", True, f"Found {len(mp4_files)} files")
        else:
            self.log_test("Existing Recordings", False, "No recordings found")
        
        # Test dual_recorder service logs
        success, stdout, stderr = self.run_command([
            "journalctl", "-u", "dual_recorder.service", "--since", "5 minutes ago", "-n", "10"
        ])
        
        if success and stdout:
            if "No active booking found" in stdout:
                self.log_test("Dual Recorder Service", True, "Running, waiting for bookings")
            elif "ERROR" in stdout or "FAILED" in stdout:
                self.log_test("Dual Recorder Service", False, "Has errors in logs")
                return False
            else:
                self.log_test("Dual Recorder Service", True, "Running normally")
        else:
            self.log_test("Dual Recorder Service", False, "No recent logs")
            return False
        
        return True
    
    def test_video_processing(self) -> bool:
        """Test 7: Test video processing functionality"""
        print("\n🎥 Testing Video Processing...")
        
        # Check video_worker service logs
        success, stdout, stderr = self.run_command([
            "journalctl", "-u", "video_worker.service", "--since", "5 minutes ago", "-n", "10"
        ])
        
        if success and stdout:
            if "Scanning directory" in stdout:
                self.log_test("Video Worker Service", True, "Scanning for videos")
            elif "ERROR" in stdout or "FAILED" in stdout:
                self.log_test("Video Worker Service", False, "Has errors in logs")
                return False
            else:
                self.log_test("Video Worker Service", True, "Running normally")
        else:
            self.log_test("Video Worker Service", False, "No recent logs")
            return False
        
        # Check processed directory
        processed_dir = Path("/opt/ezrec-backend/processed")
        if processed_dir.exists():
            self.log_test("Processed Directory", True, "Exists")
        else:
            self.log_test("Processed Directory", False, "Not found")
        
        return True
    
    def test_system_health(self) -> bool:
        """Test 8: Test system health monitoring"""
        print("\n💚 Testing System Health...")
        
        # Check system_status service
        success, stdout, stderr = self.run_command([
            "journalctl", "-u", "system_status.service", "--since", "10 minutes ago", "-n", "5"
        ])
        
        if success and stdout:
            if "Health check completed" in stdout:
                self.log_test("System Status Service", True, "Health checks running")
            else:
                self.log_test("System Status Service", False, "No health check logs")
                return False
        else:
            self.log_test("System Status Service", False, "No recent logs")
            return False
        
        # Check status.json file
        status_file = Path("/opt/ezrec-backend/status.json")
        if status_file.exists():
            try:
                with open(status_file, 'r') as f:
                    status_data = json.load(f)
                self.log_test("Status File", True, f"Status: {status_data.get('status', 'unknown')}")
            except Exception as e:
                self.log_test("Status File", False, f"Invalid JSON: {e}")
        else:
            self.log_test("Status File", False, "File not found")
        
        return True
    
    def test_disk_space(self) -> bool:
        """Test 9: Check disk space and system resources"""
        print("\n💾 Testing System Resources...")
        
        # Check disk space
        success, stdout, stderr = self.run_command(["df", "-h", "/opt/ezrec-backend"])
        if success:
            lines = stdout.strip().split('\n')
            if len(lines) > 1:
                usage_line = lines[1].split()
                if len(usage_line) >= 5:
                    usage_percent = usage_line[4]
                    self.log_test("Disk Space", True, f"Usage: {usage_percent}")
                else:
                    self.log_test("Disk Space", False, "Could not parse usage")
            else:
                self.log_test("Disk Space", False, "No usage data")
        else:
            self.log_test("Disk Space", False, f"Error: {stderr}")
        
        # Check memory usage
        success, stdout, stderr = self.run_command(["free", "-h"])
        if success:
            lines = stdout.strip().split('\n')
            if len(lines) > 1:
                mem_line = lines[1].split()
                if len(mem_line) >= 3:
                    total_mem = mem_line[1]
                    used_mem = mem_line[2]
                    self.log_test("Memory Usage", True, f"Used: {used_mem}/{total_mem}")
                else:
                    self.log_test("Memory Usage", False, "Could not parse memory")
            else:
                self.log_test("Memory Usage", False, "No memory data")
        else:
            self.log_test("Memory Usage", False, f"Error: {stderr}")
        
        return True
    
    def test_cloudflare_tunnel(self) -> bool:
        """Test 10: Test Cloudflare tunnel connectivity"""
        print("\n☁️ Testing Cloudflare Tunnel...")
        
        # Check cloudflared service
        success, stdout, stderr = self.run_command(["systemctl", "is-active", "cloudflared.service"])
        if success and stdout.strip() == "active":
            self.log_test("Cloudflare Service", True, "Running")
        else:
            self.log_test("Cloudflare Service", False, "Not running")
            return False
        
        # Check tunnel logs
        success, stdout, stderr = self.run_command([
            "journalctl", "-u", "cloudflared.service", "--since", "5 minutes ago", "-n", "5"
        ])
        
        if success and stdout:
            if "connection established" in stdout.lower() or "tunnel" in stdout.lower():
                self.log_test("Cloudflare Tunnel", True, "Connected")
            else:
                self.log_test("Cloudflare Tunnel", False, "No connection logs")
                return False
        else:
            self.log_test("Cloudflare Tunnel", False, "No recent logs")
            return False
        
        return True
    
    def create_test_recording(self) -> bool:
        """Test 11: Create a test recording to verify full functionality"""
        print("\n🎬 Creating Test Recording...")
        
        try:
            # Create a test booking for immediate recording
            now = datetime.now(pytz.timezone('America/New_York'))
            start_time = now + timedelta(seconds=30)  # Start in 30 seconds
            end_time = start_time + timedelta(minutes=1)  # Record for 1 minute
            
            booking_data = {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "title": "System Test Recording",
                "description": "Automated system test recording"
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/bookings",
                json=booking_data,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                self.log_test("Test Booking Created", True, "Scheduled for immediate recording")
                
                # Wait for recording to start
                print("⏳ Waiting for recording to start...")
                time.sleep(45)  # Wait 45 seconds
                
                # Check if recording files were created
                today = datetime.now().strftime("%Y-%m-%d")
                today_dir = self.recordings_dir / today
                
                if today_dir.exists():
                    mp4_files = list(today_dir.glob("*.mp4"))
                    if mp4_files:
                        # Check if any files were created recently
                        recent_files = [f for f in mp4_files if (datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)).seconds < 120]
                        if recent_files:
                            self.log_test("Test Recording Created", True, f"Found {len(recent_files)} recent files")
                            return True
                        else:
                            self.log_test("Test Recording Created", False, "No recent files found")
                            return False
                    else:
                        self.log_test("Test Recording Created", False, "No MP4 files found")
                        return False
                else:
                    self.log_test("Test Recording Created", False, "Today's directory not found")
                    return False
            else:
                self.log_test("Test Booking Created", False, f"API error: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Test Recording Created", False, f"Error: {e}")
            return False
    
    def generate_report(self) -> None:
        """Generate comprehensive test report"""
        print("\n" + "=" * 80)
        print("📊 EZREC SYSTEM TEST REPORT")
        print("=" * 80)
        
        test_duration = datetime.now() - self.test_start_time
        print(f"Test Duration: {test_duration}")
        print(f"Test Time: {self.test_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Count results
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result)
        failed_tests = total_tests - passed_tests
        
        print(f"\nTest Results: {passed_tests}/{total_tests} passed")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Detailed results
        print("\n📋 Detailed Results:")
        print("-" * 80)
        
        for test_name, result in self.results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
        
        # System status summary
        print("\n🎯 System Status Summary:")
        print("-" * 80)
        
        critical_tests = [
            "All Services Running",
            "Camera Detection", 
            "API Endpoints",
            "Environment Config"
        ]
        
        critical_passed = all(self.results.get(test, False) for test in critical_tests)
        
        if critical_passed and passed_tests >= total_tests * 0.8:
            print("🎉 SYSTEM STATUS: EXCELLENT - All critical components working")
            print("✅ System is ready for production use")
        elif critical_passed and passed_tests >= total_tests * 0.6:
            print("⚠️ SYSTEM STATUS: GOOD - Core functionality working")
            print("🔧 Some non-critical features may need attention")
        else:
            print("❌ SYSTEM STATUS: NEEDS ATTENTION - Critical issues detected")
            print("🚨 System requires troubleshooting before production use")
        
        # Recommendations
        print("\n💡 Recommendations:")
        print("-" * 80)
        
        if not self.results.get("All Services Running", False):
            print("🔧 Check systemd services: sudo systemctl status <service>")
        
        if not self.results.get("Camera Detection", False):
            print("📷 Check camera connections and permissions")
        
        if not self.results.get("API Endpoints", False):
            print("🌐 Check API service and port 8000")
        
        if not self.results.get("Environment Config", False):
            print("⚙️ Check .env file configuration")
        
        if not self.results.get("Cloudflare Tunnel", False):
            print("☁️ Check Cloudflare tunnel configuration")
        
        print("\n" + "=" * 80)
    
    def run_all_tests(self) -> bool:
        """Run all tests and return overall success"""
        print("🧪 EZREC COMPREHENSIVE SYSTEM TEST SUITE")
        print("=" * 80)
        print("Testing all components of the EZREC dual-camera recording system")
        print("=" * 80)
        
        # Run all tests
        tests = [
            self.test_system_services,
            self.test_camera_detection,
            self.test_api_endpoints,
            self.test_environment_configuration,
            self.test_booking_system,
            self.test_recording_functionality,
            self.test_video_processing,
            self.test_system_health,
            self.test_disk_space,
            self.test_cloudflare_tunnel,
            self.create_test_recording
        ]
        
        for test_func in tests:
            try:
                test_func()
            except Exception as e:
                test_name = test_func.__name__.replace('test_', '').replace('_', ' ').title()
                self.log_test(test_name, False, f"Test crashed: {e}")
        
        # Generate report
        self.generate_report()
        
        # Return overall success
        critical_tests = [
            "All Services Running",
            "Camera Detection", 
            "API Endpoints",
            "Environment Config"
        ]
        
        return all(self.results.get(test, False) for test in critical_tests)

def main():
    """Main function"""
    tester = EZRECSystemTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 SYSTEM TEST COMPLETED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("\n💥 SYSTEM TEST FAILED - CHECK REPORT ABOVE")
        sys.exit(1)

if __name__ == "__main__":
    main()