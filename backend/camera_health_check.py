#!/usr/bin/env python3
"""
Camera Health Check Script
- Validates both cameras are accessible
- Tests basic video capture
- Checks FFmpeg compatibility
- Provides detailed diagnostics
"""

import os
import sys
import time
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class CameraStatus(Enum):
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"

@dataclass
class CameraInfo:
    device: str
    status: CameraStatus
    name: str = ""
    capabilities: List[str] = None
    error_message: str = ""
    test_duration: float = 0.0

class CameraHealthChecker:
    """Validates camera setup and health"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cameras = {}
        
    def setup_logging(self):
        """Set up logging for health checks"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('/opt/ezrec-backend/logs/camera_health.log')
            ]
        )
    
    def check_v4l2_devices(self) -> List[str]:
        """Check available v4l2 devices"""
        try:
            result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                devices = []
                for line in result.stdout.split('\n'):
                    if '/dev/video' in line:
                        device = line.strip().split()[0]
                        devices.append(device)
                return devices
            else:
                self.logger.error(f"v4l2-ctl failed: {result.stderr}")
                return []
        except Exception as e:
            self.logger.error(f"Error checking v4l2 devices: {e}")
            return []
    
    def get_camera_capabilities(self, device: str) -> List[str]:
        """Get camera capabilities using v4l2-ctl"""
        try:
            result = subprocess.run([
                'v4l2-ctl', '--device', device, '--list-formats-ext'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                capabilities = []
                for line in result.stdout.split('\n'):
                    if 'Size:' in line or 'Pixel Format:' in line:
                        capabilities.append(line.strip())
                return capabilities
            else:
                return []
        except Exception as e:
            self.logger.warning(f"Error getting capabilities for {device}: {e}")
            return []
    
    def test_camera_capture(self, device: str, duration: int = 3) -> Tuple[bool, str, float]:
        """Test camera capture with FFmpeg"""
        start_time = time.time()
        test_file = Path(f"/tmp/camera_test_{device.replace('/', '_')}.mp4")
        
        try:
            # Create test video with FFmpeg
            cmd = [
                'ffmpeg', '-y',
                '-f', 'v4l2',
                '-i', device,
                '-t', str(duration),
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '30',
                '-pix_fmt', 'yuv420p',
                str(test_file)
            ]
            
            self.logger.info(f"🔧 Testing {device} with command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 10)
            test_duration = time.time() - start_time
            
            if result.returncode == 0 and test_file.exists():
                file_size = test_file.stat().st_size
                if file_size > 1024:  # At least 1KB
                    test_file.unlink()  # Clean up
                    return True, f"Capture successful ({file_size:,} bytes)", test_duration
                else:
                    test_file.unlink()
                    return False, f"Capture produced small file ({file_size:,} bytes)", test_duration
            else:
                if test_file.exists():
                    test_file.unlink()
                return False, f"FFmpeg failed: {result.stderr}", test_duration
                
        except subprocess.TimeoutExpired:
            if test_file.exists():
                test_file.unlink()
            return False, "Capture timed out", time.time() - start_time
        except Exception as e:
            if test_file.exists():
                test_file.unlink()
            return False, f"Capture error: {e}", time.time() - start_time
    
    def check_ffmpeg_availability(self) -> bool:
        """Check if FFmpeg is available and working"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False
    
    def validate_camera_setup(self, camera_serials: Dict[str, str]) -> Dict[str, CameraInfo]:
        """Validate complete camera setup"""
        self.logger.info("🔍 Starting camera health check...")
        
        # Check FFmpeg availability
        if not self.check_ffmpeg_availability():
            self.logger.error("❌ FFmpeg not available")
            return {}
        
        self.logger.info("✅ FFmpeg is available")
        
        # Get available v4l2 devices
        devices = self.check_v4l2_devices()
        self.logger.info(f"📷 Found v4l2 devices: {devices}")
        
        if not devices:
            self.logger.error("❌ No v4l2 devices found")
            return {}
        
        # Test each device
        camera_info = {}
        for device in devices:
            self.logger.info(f"🔧 Testing device: {device}")
            
            # Get capabilities
            capabilities = self.get_camera_capabilities(device)
            
            # Test capture
            success, error_msg, test_duration = self.test_camera_capture(device)
            
            # Create camera info
            camera_info[device] = CameraInfo(
                device=device,
                status=CameraStatus.AVAILABLE if success else CameraStatus.ERROR,
                capabilities=capabilities,
                error_message=error_msg if not success else "",
                test_duration=test_duration
            )
            
            if success:
                self.logger.info(f"✅ {device} is working correctly")
            else:
                self.logger.error(f"❌ {device} failed: {error_msg}")
        
        return camera_info
    
    def generate_health_report(self, camera_info: Dict[str, CameraInfo]) -> Dict:
        """Generate comprehensive health report"""
        total_cameras = len(camera_info)
        working_cameras = sum(1 for cam in camera_info.values() if cam.status == CameraStatus.AVAILABLE)
        
        report = {
            "timestamp": time.time(),
            "summary": {
                "total_cameras": total_cameras,
                "working_cameras": working_cameras,
                "failed_cameras": total_cameras - working_cameras,
                "health_status": "healthy" if working_cameras >= 2 else "degraded" if working_cameras >= 1 else "failed"
            },
            "cameras": {
                device: {
                    "status": cam.status.value,
                    "capabilities": cam.capabilities,
                    "error_message": cam.error_message,
                    "test_duration": cam.test_duration
                }
                for device, cam in camera_info.items()
            },
            "recommendations": []
        }
        
        # Add recommendations
        if working_cameras < 2:
            report["recommendations"].append("Need at least 2 working cameras for dual recording")
        
        if working_cameras == 0:
            report["recommendations"].append("No working cameras found. Check hardware connections")
        
        for device, cam in camera_info.items():
            if cam.status != CameraStatus.AVAILABLE:
                report["recommendations"].append(f"Fix {device}: {cam.error_message}")
        
        return report
    
    def save_health_report(self, report: Dict, file_path: Path = None):
        """Save health report to file"""
        if file_path is None:
            file_path = Path("/opt/ezrec-backend/logs/camera_health_report.json")
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"📄 Health report saved to: {file_path}")
    
    def run_full_health_check(self, camera_serials: Dict[str, str] = None) -> bool:
        """Run complete health check and return success status"""
        if camera_serials is None:
            camera_serials = {
                "camera_0": "88000",
                "camera_1": "80000"
            }
        
        self.setup_logging()
        self.logger.info("🚀 Starting full camera health check...")
        
        # Validate camera setup
        camera_info = self.validate_camera_setup(camera_serials)
        
        # Generate report
        report = self.generate_health_report(camera_info)
        
        # Save report
        self.save_health_report(report)
        
        # Print summary
        self.logger.info("=" * 60)
        self.logger.info("📊 CAMERA HEALTH SUMMARY:")
        self.logger.info(f"   Total cameras: {report['summary']['total_cameras']}")
        self.logger.info(f"   Working cameras: {report['summary']['working_cameras']}")
        self.logger.info(f"   Health status: {report['summary']['health_status']}")
        
        if report['recommendations']:
            self.logger.info("🔧 RECOMMENDATIONS:")
            for rec in report['recommendations']:
                self.logger.info(f"   - {rec}")
        
        self.logger.info("=" * 60)
        
        # Return success if we have at least 2 working cameras
        return report['summary']['working_cameras'] >= 2

def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Camera Health Check")
    parser.add_argument("--camera-0-serial", default="88000", help="Camera 0 serial number")
    parser.add_argument("--camera-1-serial", default="80000", help="Camera 1 serial number")
    parser.add_argument("--output", help="Output file for health report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Set up logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create checker and run health check
    checker = CameraHealthChecker()
    
    camera_serials = {
        "camera_0": args.camera_0_serial,
        "camera_1": args.camera_1_serial
    }
    
    success = checker.run_full_health_check(camera_serials)
    
    if success:
        print("✅ Camera health check passed")
        sys.exit(0)
    else:
        print("❌ Camera health check failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 