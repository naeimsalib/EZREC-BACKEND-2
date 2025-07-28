#!/usr/bin/env python3
"""
EZREC Camera Test Suite
- Comprehensive camera hardware testing
- Python access verification
- Image capture testing
- CLI and UI interfaces
"""

import os
import sys
import time
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime
import threading
from typing import Dict, List, Optional, Tuple

# Try to import GUI libraries
try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    from PIL import Image, ImageTk
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    print("⚠️ GUI libraries not available. Install with: pip install pillow")

# Try to import camera libraries
try:
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False
    print("❌ Picamera2 not available")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CameraTestSuite:
    """Comprehensive camera testing suite"""
    
    def __init__(self):
        self.test_results = {}
        self.camera_devices = []
        self.available_cameras = []
        
    def run_all_tests(self) -> Dict:
        """Run all camera tests and return results"""
        logger.info("🔍 Starting comprehensive camera test suite...")
        
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "hardware_tests": {},
            "python_access_tests": {},
            "image_capture_tests": {},
            "overall_status": "unknown"
        }
        
        # Run hardware detection tests
        self.test_hardware_detection()
        
        # Run Python access tests
        self.test_python_access()
        
        # Run image capture tests
        self.test_image_capture()
        
        # Determine overall status
        self.determine_overall_status()
        
        return self.test_results
    
    def test_hardware_detection(self):
        """Test camera hardware detection"""
        logger.info("🔧 Testing camera hardware detection...")
        
        # Test 1: Check for video devices
        try:
            result = subprocess.run(['ls', '/dev/video*'], capture_output=True, text=True)
            if result.returncode == 0:
                devices = result.stdout.strip().split('\n')
                self.camera_devices = [d for d in devices if d]
                self.test_results["hardware_tests"]["video_devices"] = {
                    "status": "pass",
                    "devices": self.camera_devices,
                    "count": len(self.camera_devices)
                }
                logger.info(f"✅ Found {len(self.camera_devices)} video devices")
            else:
                self.test_results["hardware_tests"]["video_devices"] = {
                    "status": "fail",
                    "error": "No video devices found"
                }
                logger.error("❌ No video devices found")
        except Exception as e:
            self.test_results["hardware_tests"]["video_devices"] = {
                "status": "error",
                "error": str(e)
            }
            logger.error(f"❌ Error checking video devices: {e}")
        
        # Test 2: Check camera info
        try:
            result = subprocess.run(['v4l2-ctl', '--list-devices'], capture_output=True, text=True)
            if result.returncode == 0:
                self.test_results["hardware_tests"]["camera_info"] = {
                    "status": "pass",
                    "info": result.stdout
                }
                logger.info("✅ Camera info retrieved successfully")
            else:
                self.test_results["hardware_tests"]["camera_info"] = {
                    "status": "fail",
                    "error": "Failed to get camera info"
                }
                logger.error("❌ Failed to get camera info")
        except Exception as e:
            self.test_results["hardware_tests"]["camera_info"] = {
                "status": "error",
                "error": str(e)
            }
            logger.error(f"❌ Error getting camera info: {e}")
        
        # Test 3: Check camera capabilities
        try:
            capabilities = {}
            for device in self.camera_devices[:3]:  # Test first 3 devices
                try:
                    result = subprocess.run(['v4l2-ctl', '--device', device, '--list-formats-ext'], 
                                         capture_output=True, text=True)
                    if result.returncode == 0:
                        capabilities[device] = result.stdout
                    else:
                        capabilities[device] = f"Error: {result.stderr}"
                except Exception as e:
                    capabilities[device] = f"Exception: {e}"
            
            self.test_results["hardware_tests"]["camera_capabilities"] = {
                "status": "pass" if capabilities else "fail",
                "capabilities": capabilities
            }
            logger.info("✅ Camera capabilities checked")
        except Exception as e:
            self.test_results["hardware_tests"]["camera_capabilities"] = {
                "status": "error",
                "error": str(e)
            }
            logger.error(f"❌ Error checking camera capabilities: {e}")
    
    def test_python_access(self):
        """Test Python camera access"""
        logger.info("🐍 Testing Python camera access...")
        
        if not CAMERA_AVAILABLE:
            self.test_results["python_access_tests"]["picamera2_import"] = {
                "status": "fail",
                "error": "Picamera2 not available"
            }
            logger.error("❌ Picamera2 not available")
            return
        
        # Test 1: Import test
        try:
            from picamera2 import Picamera2
            self.test_results["python_access_tests"]["picamera2_import"] = {
                "status": "pass"
            }
            logger.info("✅ Picamera2 import successful")
        except Exception as e:
            self.test_results["python_access_tests"]["picamera2_import"] = {
                "status": "fail",
                "error": str(e)
            }
            logger.error(f"❌ Picamera2 import failed: {e}")
            return
        
        # Test 2: Camera creation test
        try:
            camera = Picamera2()
            self.test_results["python_access_tests"]["camera_creation"] = {
                "status": "pass"
            }
            logger.info("✅ Camera creation successful")
            camera.close()
        except Exception as e:
            self.test_results["python_access_tests"]["camera_creation"] = {
                "status": "fail",
                "error": str(e)
            }
            logger.error(f"❌ Camera creation failed: {e}")
        
        # Test 3: Camera configuration test
        try:
            camera = Picamera2()
            config = camera.create_video_configuration(
                main={"size": (1920, 1080), "format": "YUV420"}
            )
            camera.configure(config)
            camera.start()
            camera.stop()
            camera.close()
            
            self.test_results["python_access_tests"]["camera_configuration"] = {
                "status": "pass"
            }
            logger.info("✅ Camera configuration successful")
        except Exception as e:
            self.test_results["python_access_tests"]["camera_configuration"] = {
                "status": "fail",
                "error": str(e)
            }
            logger.error(f"❌ Camera configuration failed: {e}")
        
        # Test 4: Multiple camera test
        try:
            cameras = []
            for i in range(2):  # Try to create 2 cameras
                try:
                    camera = Picamera2()
                    cameras.append(camera)
                    logger.info(f"✅ Camera {i} created successfully")
                except Exception as e:
                    logger.warning(f"⚠️ Camera {i} creation failed: {e}")
                    break
            
            # Clean up
            for camera in cameras:
                try:
                    camera.close()
                except:
                    pass
            
            self.test_results["python_access_tests"]["multiple_cameras"] = {
                "status": "pass" if len(cameras) > 0 else "fail",
                "cameras_created": len(cameras)
            }
            logger.info(f"✅ Created {len(cameras)} camera(s)")
        except Exception as e:
            self.test_results["python_access_tests"]["multiple_cameras"] = {
                "status": "error",
                "error": str(e)
            }
            logger.error(f"❌ Multiple camera test failed: {e}")
    
    def test_image_capture(self):
        """Test image capture functionality"""
        logger.info("📸 Testing image capture...")
        
        if not CAMERA_AVAILABLE:
            self.test_results["image_capture_tests"]["capture_test"] = {
                "status": "fail",
                "error": "Picamera2 not available"
            }
            return
        
        # Test 1: Basic image capture
        try:
            camera = Picamera2()
            config = camera.create_video_configuration(
                main={"size": (1920, 1080), "format": "YUV420"}
            )
            camera.configure(config)
            camera.start()
            
            # Capture image
            image = camera.capture_array()
            camera.stop()
            camera.close()
            
            # Check image properties
            if image is not None and image.size > 0:
                self.test_results["image_capture_tests"]["capture_test"] = {
                    "status": "pass",
                    "image_shape": image.shape,
                    "image_size": image.size
                }
                logger.info(f"✅ Image capture successful: {image.shape}")
            else:
                self.test_results["image_capture_tests"]["capture_test"] = {
                    "status": "fail",
                    "error": "Captured image is empty"
                }
                logger.error("❌ Captured image is empty")
        except Exception as e:
            self.test_results["image_capture_tests"]["capture_test"] = {
                "status": "fail",
                "error": str(e)
            }
            logger.error(f"❌ Image capture failed: {e}")
        
        # Test 2: Video recording test
        try:
            camera = Picamera2()
            config = camera.create_video_configuration(
                main={"size": (1920, 1080), "format": "YUV420"}
            )
            camera.configure(config)
            camera.start()
            
            # Create encoder
            encoder = H264Encoder(bitrate=6000000)
            
            # Start recording
            test_file = "/tmp/camera_test_recording.mp4"
            camera.start_recording(encoder, test_file)
            
            # Record for 2 seconds
            time.sleep(2)
            
            # Stop recording
            camera.stop_recording()
            camera.stop()
            camera.close()
            
            # Check if file was created and has content
            if os.path.exists(test_file):
                file_size = os.path.getsize(test_file)
                if file_size > 0:
                    self.test_results["image_capture_tests"]["video_recording"] = {
                        "status": "pass",
                        "file_size": file_size
                    }
                    logger.info(f"✅ Video recording successful: {file_size} bytes")
                    
                    # Clean up test file
                    os.remove(test_file)
                else:
                    self.test_results["image_capture_tests"]["video_recording"] = {
                        "status": "fail",
                        "error": "Recording file is empty"
                    }
                    logger.error("❌ Recording file is empty")
            else:
                self.test_results["image_capture_tests"]["video_recording"] = {
                    "status": "fail",
                    "error": "Recording file not created"
                }
                logger.error("❌ Recording file not created")
        except Exception as e:
            self.test_results["image_capture_tests"]["video_recording"] = {
                "status": "fail",
                "error": str(e)
            }
            logger.error(f"❌ Video recording failed: {e}")
    
    def determine_overall_status(self):
        """Determine overall test status"""
        all_tests = []
        
        # Collect all test results
        for category in self.test_results.values():
            if isinstance(category, dict) and "status" in category:
                all_tests.append(category["status"])
            elif isinstance(category, dict):
                for test in category.values():
                    if isinstance(test, dict) and "status" in test:
                        all_tests.append(test["status"])
        
        # Determine overall status
        if not all_tests:
            self.test_results["overall_status"] = "unknown"
        elif all(status == "pass" for status in all_tests):
            self.test_results["overall_status"] = "pass"
        elif any(status == "fail" for status in all_tests):
            self.test_results["overall_status"] = "fail"
        else:
            self.test_results["overall_status"] = "partial"
        
        logger.info(f"🎯 Overall test status: {self.test_results['overall_status']}")
    
    def save_results(self, filename: str = None):
        """Save test results to file"""
        if filename is None:
            filename = f"camera_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        logger.info(f"💾 Test results saved to: {filename}")
        return filename
    
    def print_results(self):
        """Print test results in a readable format"""
        print("\n" + "="*60)
        print("📊 CAMERA TEST SUITE RESULTS")
        print("="*60)
        
        print(f"⏰ Timestamp: {self.test_results['timestamp']}")
        print(f"🎯 Overall Status: {self.test_results['overall_status'].upper()}")
        print()
        
        # Hardware tests
        print("🔧 HARDWARE TESTS:")
        for test_name, result in self.test_results.get("hardware_tests", {}).items():
            status = result.get("status", "unknown")
            status_icon = "✅" if status == "pass" else "❌" if status == "fail" else "⚠️"
            print(f"  {status_icon} {test_name}: {status}")
            if "error" in result:
                print(f"     Error: {result['error']}")
        print()
        
        # Python access tests
        print("🐍 PYTHON ACCESS TESTS:")
        for test_name, result in self.test_results.get("python_access_tests", {}).items():
            status = result.get("status", "unknown")
            status_icon = "✅" if status == "pass" else "❌" if status == "fail" else "⚠️"
            print(f"  {status_icon} {test_name}: {status}")
            if "error" in result:
                print(f"     Error: {result['error']}")
        print()
        
        # Image capture tests
        print("📸 IMAGE CAPTURE TESTS:")
        for test_name, result in self.test_results.get("image_capture_tests", {}).items():
            status = result.get("status", "unknown")
            status_icon = "✅" if status == "pass" else "❌" if status == "fail" else "⚠️"
            print(f"  {status_icon} {test_name}: {status}")
            if "error" in result:
                print(f"     Error: {result['error']}")
        print("="*60)

class CameraTestGUI:
    """GUI interface for camera testing"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("EZREC Camera Test Suite")
        self.root.geometry("800x600")
        
        self.test_suite = CameraTestSuite()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the GUI interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="EZREC Camera Test Suite", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Test buttons
        ttk.Button(main_frame, text="🔧 Test Hardware Detection", 
                  command=self.test_hardware).grid(row=1, column=0, pady=5, padx=5, sticky=tk.W+tk.E)
        
        ttk.Button(main_frame, text="🐍 Test Python Access", 
                  command=self.test_python).grid(row=2, column=0, pady=5, padx=5, sticky=tk.W+tk.E)
        
        ttk.Button(main_frame, text="📸 Test Image Capture", 
                  command=self.test_capture).grid(row=3, column=0, pady=5, padx=5, sticky=tk.W+tk.E)
        
        ttk.Button(main_frame, text="🎯 Run All Tests", 
                  command=self.run_all_tests).grid(row=4, column=0, pady=5, padx=5, sticky=tk.W+tk.E)
        
        ttk.Button(main_frame, text="💾 Save Results", 
                  command=self.save_results).grid(row=5, column=0, pady=5, padx=5, sticky=tk.W+tk.E)
        
        # Results text area
        self.results_text = tk.Text(main_frame, height=20, width=80)
        self.results_text.grid(row=1, column=1, rowspan=5, pady=5, padx=10, sticky=tk.W+tk.E+tk.N+tk.S)
        
        # Scrollbar for results
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.results_text.yview)
        scrollbar.grid(row=1, column=2, rowspan=5, sticky=tk.N+tk.S)
        self.results_text.configure(yscrollcommand=scrollbar.set)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=6, column=0, columnspan=3, sticky=tk.W+tk.E, pady=(10, 0))
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
    
    def test_hardware(self):
        """Test hardware detection"""
        self.status_var.set("Testing hardware detection...")
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "🔧 Testing hardware detection...\n")
        self.root.update()
        
        self.test_suite.test_hardware_detection()
        self.display_results()
    
    def test_python(self):
        """Test Python access"""
        self.status_var.set("Testing Python access...")
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "🐍 Testing Python access...\n")
        self.root.update()
        
        self.test_suite.test_python_access()
        self.display_results()
    
    def test_capture(self):
        """Test image capture"""
        self.status_var.set("Testing image capture...")
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "📸 Testing image capture...\n")
        self.root.update()
        
        self.test_suite.test_image_capture()
        self.display_results()
    
    def run_all_tests(self):
        """Run all tests"""
        self.status_var.set("Running all tests...")
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "🎯 Running all tests...\n")
        self.root.update()
        
        self.test_suite.run_all_tests()
        self.display_results()
    
    def display_results(self):
        """Display test results in the GUI"""
        self.results_text.delete(1.0, tk.END)
        
        results = self.test_suite.test_results
        self.results_text.insert(tk.END, f"📊 Test Results\n")
        self.results_text.insert(tk.END, f"⏰ Timestamp: {results.get('timestamp', 'N/A')}\n")
        self.results_text.insert(tk.END, f"🎯 Overall Status: {results.get('overall_status', 'unknown').upper()}\n\n")
        
        # Display hardware tests
        self.results_text.insert(tk.END, "🔧 HARDWARE TESTS:\n")
        for test_name, result in results.get("hardware_tests", {}).items():
            status = result.get("status", "unknown")
            status_icon = "✅" if status == "pass" else "❌" if status == "fail" else "⚠️"
            self.results_text.insert(tk.END, f"  {status_icon} {test_name}: {status}\n")
            if "error" in result:
                self.results_text.insert(tk.END, f"     Error: {result['error']}\n")
        self.results_text.insert(tk.END, "\n")
        
        # Display Python tests
        self.results_text.insert(tk.END, "🐍 PYTHON ACCESS TESTS:\n")
        for test_name, result in results.get("python_access_tests", {}).items():
            status = result.get("status", "unknown")
            status_icon = "✅" if status == "pass" else "❌" if status == "fail" else "⚠️"
            self.results_text.insert(tk.END, f"  {status_icon} {test_name}: {status}\n")
            if "error" in result:
                self.results_text.insert(tk.END, f"     Error: {result['error']}\n")
        self.results_text.insert(tk.END, "\n")
        
        # Display capture tests
        self.results_text.insert(tk.END, "📸 IMAGE CAPTURE TESTS:\n")
        for test_name, result in results.get("image_capture_tests", {}).items():
            status = result.get("status", "unknown")
            status_icon = "✅" if status == "pass" else "❌" if status == "fail" else "⚠️"
            self.results_text.insert(tk.END, f"  {status_icon} {test_name}: {status}\n")
            if "error" in result:
                self.results_text.insert(tk.END, f"     Error: {result['error']}\n")
        
        self.status_var.set("Tests completed")
    
    def save_results(self):
        """Save test results"""
        filename = self.test_suite.save_results()
        messagebox.showinfo("Save Results", f"Results saved to: {filename}")
    
    def run(self):
        """Run the GUI"""
        self.root.mainloop()

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="EZREC Camera Test Suite")
    parser.add_argument("--gui", action="store_true", help="Run GUI interface")
    parser.add_argument("--save", action="store_true", help="Save results to file")
    parser.add_argument("--output", help="Output file for results")
    
    args = parser.parse_args()
    
    test_suite = CameraTestSuite()
    
    if args.gui:
        if not GUI_AVAILABLE:
            print("❌ GUI not available. Install pillow: pip install pillow")
            return
        
        print("🖥️ Starting GUI interface...")
        gui = CameraTestGUI()
        gui.run()
    else:
        print("🔍 Running camera test suite...")
        results = test_suite.run_all_tests()
        test_suite.print_results()
        
        if args.save:
            filename = test_suite.save_results(args.output)
            print(f"💾 Results saved to: {filename}")

if __name__ == "__main__":
    main() 