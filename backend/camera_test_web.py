#!/usr/bin/env python3
"""
Web-based Camera Test Interface
- Access via browser for easy testing
- Real-time camera status
- Image capture and display
"""

import os
import sys
import json
import time
import base64
import threading
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request, Response
import cv2
import numpy as np

# Try to import camera libraries
try:
    from picamera2 import Picamera2
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False

app = Flask(__name__)

# Global camera instance
camera = None
camera_lock = threading.Lock()

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>EZREC Camera Test Suite</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
        .header { text-align: center; color: #333; margin-bottom: 30px; }
        .test-section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .test-button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
        .test-button:hover { background: #0056b3; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .status.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .status.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .status.warning { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
        .camera-feed { text-align: center; margin: 20px 0; }
        .camera-feed img { max-width: 100%; border: 2px solid #ddd; border-radius: 5px; }
        .log { background: #f8f9fa; padding: 10px; border-radius: 5px; font-family: monospace; max-height: 300px; overflow-y: auto; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📷 EZREC Camera Test Suite</h1>
            <p>Comprehensive camera hardware and software testing</p>
        </div>

        <div class="test-section">
            <h3>🔧 Hardware Tests</h3>
            <button class="test-button" onclick="runTest('hardware')">Test Hardware Detection</button>
            <button class="test-button" onclick="runTest('devices')">List Video Devices</button>
            <button class="test-button" onclick="runTest('info')">Get Camera Info</button>
            <div id="hardware-results"></div>
        </div>

        <div class="test-section">
            <h3>🐍 Python Access Tests</h3>
            <button class="test-button" onclick="runTest('python')">Test Python Access</button>
            <button class="test-button" onclick="runTest('import')">Test Imports</button>
            <div id="python-results"></div>
        </div>

        <div class="test-section">
            <h3>📸 Image Capture Tests</h3>
            <button class="test-button" onclick="runTest('capture')">Capture Image</button>
            <button class="test-button" onclick="runTest('video')">Test Video Recording</button>
            <div id="capture-results"></div>
            <div class="camera-feed" id="camera-feed"></div>
        </div>

        <div class="test-section">
            <h3>🎯 Comprehensive Tests</h3>
            <button class="test-button" onclick="runTest('all')">Run All Tests</button>
            <button class="test-button" onclick="runTest('status')">Check System Status</button>
            <div id="comprehensive-results"></div>
        </div>

        <div class="test-section">
            <h3>📋 Test Log</h3>
            <div class="log" id="test-log"></div>
        </div>
    </div>

    <script>
        function log(message, type = 'info') {
            const logDiv = document.getElementById('test-log');
            const timestamp = new Date().toLocaleTimeString();
            const color = type === 'error' ? 'red' : type === 'success' ? 'green' : 'blue';
            logDiv.innerHTML += `<div style="color: ${color}">[${timestamp}] ${message}</div>`;
            logDiv.scrollTop = logDiv.scrollHeight;
        }

        function showResult(elementId, message, type = 'info') {
            const element = document.getElementById(elementId);
            element.innerHTML = `<div class="status ${type}">${message}</div>`;
        }

        async function runTest(testType) {
            log(`Starting ${testType} test...`);
            
            try {
                const response = await fetch(`/api/test/${testType}`, {
                    method: 'POST'
                });
                
                const result = await response.json();
                
                if (result.success) {
                    log(`✅ ${testType} test completed successfully`, 'success');
                    showResult(`${testType}-results`, result.message, 'success');
                    
                    if (result.image) {
                        document.getElementById('camera-feed').innerHTML = 
                            `<img src="data:image/jpeg;base64,${result.image}" alt="Camera Feed">`;
                    }
                } else {
                    log(`❌ ${testType} test failed: ${result.error}`, 'error');
                    showResult(`${testType}-results`, `Error: ${result.error}`, 'error');
                }
            } catch (error) {
                log(`❌ ${testType} test error: ${error}`, 'error');
                showResult(`${testType}-results`, `Error: ${error}`, 'error');
            }
        }

        // Auto-refresh status every 30 seconds
        setInterval(() => {
            runTest('status');
        }, 30000);
    </script>
</body>
</html>
"""

def test_hardware_detection():
    """Test camera hardware detection"""
    try:
        import subprocess
        
        # Check video devices
        result = subprocess.run(['ls', '/dev/video*'], capture_output=True, text=True)
        if result.returncode == 0:
            devices = result.stdout.strip().split('\n')
            devices = [d for d in devices if d]
            
            # Get camera info
            info_result = subprocess.run(['v4l2-ctl', '--list-devices'], capture_output=True, text=True)
            camera_info = info_result.stdout if info_result.returncode == 0 else "Failed to get camera info"
            
            return {
                "success": True,
                "message": f"Found {len(devices)} video devices",
                "devices": devices,
                "camera_info": camera_info
            }
        else:
            return {
                "success": False,
                "error": "No video devices found"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def test_python_access():
    """Test Python camera access"""
    try:
        if not CAMERA_AVAILABLE:
            return {
                "success": False,
                "error": "Picamera2 not available"
            }
        
        from picamera2 import Picamera2
        
        # Test camera creation
        camera = Picamera2()
        camera.close()
        
        return {
            "success": True,
            "message": "Python camera access successful"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def capture_image():
    """Capture an image from the camera"""
    try:
        if not CAMERA_AVAILABLE:
            return {
                "success": False,
                "error": "Picamera2 not available"
            }
        
        from picamera2 import Picamera2
        
        with camera_lock:
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
            
            # Convert to JPEG
            if image is not None and image.size > 0:
                # Convert YUV to RGB
                rgb_image = cv2.cvtColor(image, cv2.COLOR_YUV420p2RGB)
                
                # Encode to JPEG
                _, buffer = cv2.imencode('.jpg', rgb_image)
                jpeg_data = base64.b64encode(buffer).decode('utf-8')
                
                return {
                    "success": True,
                    "message": f"Image captured successfully: {image.shape}",
                    "image": jpeg_data
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to capture image"
                }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def test_video_recording():
    """Test video recording"""
    try:
        if not CAMERA_AVAILABLE:
            return {
                "success": False,
                "error": "Picamera2 not available"
            }
        
        from picamera2 import Picamera2
        from picamera2.encoders import H264Encoder
        
        with camera_lock:
            camera = Picamera2()
            config = camera.create_video_configuration(
                main={"size": (1920, 1080), "format": "YUV420"}
            )
            camera.configure(config)
            camera.start()
            
            # Create encoder
            encoder = H264Encoder(bitrate=6000000)
            
            # Start recording
            test_file = "/tmp/web_camera_test.mp4"
            camera.start_recording(encoder, test_file)
            
            # Record for 2 seconds
            time.sleep(2)
            
            # Stop recording
            camera.stop_recording()
            camera.stop()
            camera.close()
            
            # Check result
            if os.path.exists(test_file):
                file_size = os.path.getsize(test_file)
                if file_size > 0:
                    # Clean up
                    os.remove(test_file)
                    return {
                        "success": True,
                        "message": f"Video recording successful: {file_size} bytes"
                    }
                else:
                    return {
                        "success": False,
                        "error": "Video recording failed - empty file"
                    }
            else:
                return {
                    "success": False,
                    "error": "Video recording failed - file not created"
                }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def get_system_status():
    """Get overall system status"""
    status = {
        "timestamp": datetime.now().isoformat(),
        "camera_available": CAMERA_AVAILABLE,
        "hardware_tests": {},
        "python_tests": {},
        "capture_tests": {}
    }
    
    # Run hardware tests
    hw_result = test_hardware_detection()
    status["hardware_tests"] = hw_result
    
    # Run Python tests
    py_result = test_python_access()
    status["python_tests"] = py_result
    
    # Run capture test
    cap_result = capture_image()
    status["capture_tests"] = cap_result
    
    return status

@app.route('/')
def index():
    """Main page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/test/<test_type>', methods=['POST'])
def run_test(test_type):
    """API endpoint for running tests"""
    try:
        if test_type == 'hardware':
            result = test_hardware_detection()
        elif test_type == 'python':
            result = test_python_access()
        elif test_type == 'capture':
            result = capture_image()
        elif test_type == 'video':
            result = test_video_recording()
        elif test_type == 'status':
            result = get_system_status()
        elif test_type == 'all':
            # Run all tests
            hw_result = test_hardware_detection()
            py_result = test_python_access()
            cap_result = capture_image()
            
            all_passed = hw_result["success"] and py_result["success"] and cap_result["success"]
            
            result = {
                "success": all_passed,
                "message": f"All tests completed. {'All passed' if all_passed else 'Some failed'}",
                "hardware": hw_result,
                "python": py_result,
                "capture": cap_result
            }
        else:
            result = {
                "success": False,
                "error": f"Unknown test type: {test_type}"
            }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

if __name__ == '__main__':
    print("🌐 Starting EZREC Camera Test Web Interface...")
    print("📱 Open your browser and go to: http://localhost:5000")
    print("🔧 Press Ctrl+C to stop the server")
    
    app.run(host='0.0.0.0', port=5000, debug=True) 