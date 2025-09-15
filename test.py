#!/usr/bin/env python3
"""
EZREC Comprehensive System Test Suite
Automated testing with booking creation, log collection, and system verification
"""

import os
import sys
import time
import json
import subprocess
import datetime
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ezrec_test")

class EZRECSystemTester:
    """Comprehensive EZREC system tester"""
    
    def __init__(self):
        self.logs_file = Path("logs.txt")
        self.recordings_path = Path("/opt/ezrec-backend/recordings")
        self.bookings_path = Path("/opt/ezrec-backend/api/local_data/bookings.json")
        self.test_results = {}
        
    def log_output(self, message, command=None, output=None):
        """Log output to both console and logs.txt file"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        if command:
            log_entry += f"Command: {command}\n"
        if output:
            log_entry += f"Output: {output}\n"
        
        log_entry += "\n" + "="*80 + "\n"
        
        # Print to console
        print(log_entry.strip())
        
        # Append to logs.txt
        with open(self.logs_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
    
    def run_command(self, command, timeout=30):
        """Run a command and return output"""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)
    
    def test_system_services(self):
        """Test if all EZREC services are running"""
        self.log_output("🔍 Testing EZREC Services Status")
        
        services = [
            "dual_recorder.service",
            "video_worker.service", 
            "ezrec-api.service",
            "system_status.service",
            "cloudflared.service"
        ]
        
        results = {}
        for service in services:
            returncode, stdout, stderr = self.run_command(f"systemctl is-active {service}")
            status = "active" if returncode == 0 else "inactive"
            results[service] = status
            
            self.log_output(f"Service {service}: {status}")
        
        self.test_results["services"] = results
        return all(status == "active" for status in results.values())
    
    def test_camera_detection(self):
        """Test camera detection and availability"""
        self.log_output("📷 Testing Camera Detection")
        
        # Test camera devices
        returncode, stdout, stderr = self.run_command("ls -la /dev/video*")
        self.log_output("Camera devices:", "ls -la /dev/video*", stdout)
        
        # Test rpicam-vid detection
        self.log_output("Testing rpicam-vid camera detection...")
        returncode, stdout, stderr = self.run_command("rpicam-vid --list-cameras", timeout=60)
        
        camera_detected = returncode == 0 and ("imx477" in stdout.lower() or "camera" in stdout.lower())
        self.log_output("rpicam-vid Detection:", "rpicam-vid --list-cameras", stdout)
        
        if stderr:
            self.log_output("rpicam-vid stderr:", "", stderr)
        
        self.test_results["camera_detection"] = {
            "devices_found": returncode == 0,
            "rpicam_detection": camera_detected,
            "output": stdout
        }
        
        return camera_detected
    
    def test_api_endpoints(self):
        """Test all API endpoints"""
        self.log_output("🌐 Testing API Endpoints")
        
        endpoints = [
            "/test-alive",
            "/status", 
            "/api/bookings",
            "/api/cameras",
            "/api/recordings"
        ]
        
        results = {}
        for endpoint in endpoints:
            returncode, stdout, stderr = self.run_command(f"curl -s http://localhost:8000{endpoint}")
            success = returncode == 0 and stdout.strip()
            results[endpoint] = {
                "success": success,
                "response": stdout[:200] + "..." if len(stdout) > 200 else stdout
            }
            
            self.log_output(f"API {endpoint}: {'✅' if success else '❌'}", 
                          f"curl -s http://localhost:8000{endpoint}", 
                          stdout)
        
        self.test_results["api_endpoints"] = results
        return all(result["success"] for result in results.values())
    
    def create_test_booking(self):
        """Create a test booking starting in 1 minute"""
        self.log_output("📋 Creating Test Booking")
        
        # Calculate start time (1 minute from now)
        now = datetime.datetime.now()
        start_time = now + datetime.timedelta(minutes=1)
        end_time = start_time + datetime.timedelta(minutes=2)
        
        # Generate unique booking ID
        booking_id = f"test-{int(time.time())}"
        
        booking_data = [
            {
                "id": booking_id,
                "user_id": "test-user",
                "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "end_time": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "date": start_time.strftime("%Y-%m-%d"),
                "camera_id": "test-camera",
                "recording_id": f"rec-{booking_id}",
                "status": None,
                "email": None,
                "created_at": now.strftime("%Y-%m-%dT%H:%M:%S"),
                "updated_at": now.strftime("%Y-%m-%dT%H:%M:%S")
            }
        ]
        
        # Ensure bookings directory exists
        self.bookings_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write booking to file
        with open(self.bookings_path, 'w') as f:
            json.dump(booking_data, f, indent=2)
        
        self.log_output(f"Created test booking: {booking_id}")
        self.log_output(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_output(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.test_results["booking"] = {
            "id": booking_id,
            "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "end_time": end_time.strftime("%Y-%m-%dT%H:%M:%S")
        }
        
        return booking_id, start_time, end_time
    
    def monitor_recording_logs(self, booking_id, start_time, end_time, duration_minutes=5):
        """Monitor recording logs during the test period"""
        self.log_output(f"📹 Monitoring Recording Logs for {booking_id}")
        
        # Wait for booking to start
        wait_seconds = (start_time - datetime.datetime.now()).total_seconds()
        if wait_seconds > 0:
            self.log_output(f"⏳ Waiting {wait_seconds:.0f} seconds for booking to start...")
            time.sleep(wait_seconds)
        
        # Monitor for the duration
        monitor_duration = duration_minutes * 60
        start_monitor = time.time()
        
        self.log_output("🎬 Starting recording monitoring...")
        
        while time.time() - start_monitor < monitor_duration:
            # Get dual_recorder logs
            returncode, stdout, stderr = self.run_command(
                "journalctl -u dual_recorder.service -n 20 --no-pager"
            )
            if stdout:
                self.log_output("Dual Recorder Logs:", "journalctl -u dual_recorder.service -n 20", stdout)
            
            # Get video_worker logs
            returncode, stdout, stderr = self.run_command(
                "journalctl -u video_worker.service -n 10 --no-pager"
            )
            if stdout:
                self.log_output("Video Worker Logs:", "journalctl -u video_worker.service -n 10", stdout)
            
            # Check for recording files
            if self.recordings_path.exists():
                returncode, stdout, stderr = self.run_command(f"find {self.recordings_path} -name '*.mp4' -newer /tmp/test_start 2>/dev/null | head -10")
                if stdout:
                    self.log_output("New Recording Files:", "find recordings -name '*.mp4'", stdout)
            
            # Check recording processes
            returncode, stdout, stderr = self.run_command("ps aux | grep rpicam-vid | grep -v grep")
            if stdout:
                self.log_output("Recording Processes:", "ps aux | grep rpicam-vid", stdout)
            
            time.sleep(10)  # Check every 10 seconds
        
        self.log_output("✅ Recording monitoring completed")
    
    def test_system_resources(self):
        """Test system resources"""
        self.log_output("💻 Testing System Resources")
        
        # Disk space
        returncode, stdout, stderr = self.run_command("df -h")
        self.log_output("Disk Usage:", "df -h", stdout)
        
        # Memory usage
        returncode, stdout, stderr = self.run_command("free -h")
        self.log_output("Memory Usage:", "free -h", stdout)
        
        # CPU usage
        returncode, stdout, stderr = self.run_command("top -bn1 | head -20")
        self.log_output("CPU Usage:", "top -bn1", stdout)
        
        self.test_results["system_resources"] = {
            "disk": stdout if returncode == 0 else "Failed to get disk info",
            "memory": stdout if returncode == 0 else "Failed to get memory info"
        }
    
    def cleanup_test_data(self):
        """Clean up test data"""
        self.log_output("🧹 Cleaning up test data")
        
        # Clear booking cache
        if self.bookings_path.exists():
            self.bookings_path.unlink()
            self.log_output("Cleared booking cache")
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        self.log_output("📊 Generating Test Report")
        
        report = {
            "test_timestamp": datetime.datetime.now().isoformat(),
            "test_results": self.test_results,
            "summary": {
                "services_running": self.test_results.get("services", {}),
                "camera_detected": self.test_results.get("camera_detection", {}).get("rpicam_detection", False),
                "api_endpoints_working": all(
                    result.get("success", False) 
                    for result in self.test_results.get("api_endpoints", {}).values()
                ),
                "booking_created": "booking" in self.test_results
            }
        }
        
        # Save report
        with open("test_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        self.log_output("Test Report Summary:")
        self.log_output(f"Services: {report['summary']['services_running']}")
        self.log_output(f"Camera Detected: {report['summary']['camera_detected']}")
        self.log_output(f"API Endpoints: {report['summary']['api_endpoints_working']}")
        self.log_output(f"Booking Created: {report['summary']['booking_created']}")
        
        return report

def main():
    """Main test function"""
    print("🚀 Starting EZREC Comprehensive System Test")
    print("="*80)
    
    # Clear logs.txt
    logs_file = Path("logs.txt")
    if logs_file.exists():
        logs_file.unlink()
        print("🧹 Cleared logs.txt file")
    
    # Create test start marker
    Path("/tmp/test_start").touch()
    
    tester = EZRECSystemTester()
    
    try:
        # Test 1: System Services
        print("\n1️⃣ Testing System Services...")
        tester.test_system_services()
        
        # Test 2: Camera Detection
        print("\n2️⃣ Testing Camera Detection...")
        tester.test_camera_detection()
        
        # Test 3: API Endpoints
        print("\n3️⃣ Testing API Endpoints...")
        tester.test_api_endpoints()
        
        # Test 4: Create Test Booking
        print("\n4️⃣ Creating Test Booking...")
        booking_id, start_time, end_time = tester.create_test_booking()
        
        # Test 5: Monitor Recording
        print("\n5️⃣ Monitoring Recording...")
        tester.monitor_recording_logs(booking_id, start_time, end_time)
        
        # Test 6: System Resources
        print("\n6️⃣ Testing System Resources...")
        tester.test_system_resources()
        
        # Generate Report
        print("\n7️⃣ Generating Test Report...")
        report = tester.generate_test_report()
        
        print("\n✅ Test completed successfully!")
        print(f"📄 Full logs saved to: {tester.logs_file}")
        print(f"📊 Test report saved to: test_report.json")
        
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        tester.log_output("Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        tester.log_output(f"Test failed with error: {e}")
    finally:
        # Cleanup
        tester.cleanup_test_data()
        if Path("/tmp/test_start").exists():
            Path("/tmp/test_start").unlink()

if __name__ == "__main__":
    main()
