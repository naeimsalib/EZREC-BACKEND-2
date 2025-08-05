#!/usr/bin/env python3
"""
EZREC - OpenCV Camera Streamer
Replaces Picamera2 with OpenCV for better reliability on Raspberry Pi 5
"""

import cv2
import time
import threading
import signal
import sys
import logging
from queue import Queue, Empty
from pathlib import Path
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/opt/ezrec-backend/.env", override=True)

# Configuration
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_FPS = 30
FRAME_QUEUE_SIZE = 10
BLACK_FRAME_DURATION = 5  # seconds to show black frame if camera fails

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("/opt/ezrec-backend/logs/camera_streamer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("camera_streamer")

class OpenCVCameraStreamer:
    def __init__(self):
        self.cap = None
        self.frame_queue = Queue(maxsize=FRAME_QUEUE_SIZE)
        self.running = False
        self.capture_thread = None
        self.camera_ready = False
        self.last_frame_time = 0
        self.black_frame = None
        self._create_black_frame()
        
    def _create_black_frame(self):
        """Create a black frame for fallback"""
        self.black_frame = np.zeros((CAMERA_HEIGHT, CAMERA_WIDTH, 3), dtype=np.uint8)
        # Add some text to indicate camera issue
        cv2.putText(self.black_frame, "Camera Unavailable", 
                   (CAMERA_WIDTH//2 - 150, CAMERA_HEIGHT//2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
    def start(self):
        """Start the camera streamer"""
        logger.info("Starting OpenCV camera streamer...")
        
        try:
            # Initialize camera
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                logger.error("Failed to open camera with OpenCV")
                self.camera_ready = False
                return False
                
            # Configure camera settings
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            self.cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency
            
            # Verify camera settings
            actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            logger.info(f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps}fps")
            
            # Test frame capture
            ret, test_frame = self.cap.read()
            if ret and test_frame is not None:
                logger.info(f"✅ Camera test successful: {test_frame.shape}")
                self.camera_ready = True
            else:
                logger.warning("Camera test failed, will use fallback mode")
                self.camera_ready = False
                
        except Exception as e:
            logger.error(f"Camera initialization failed: {e}")
            self.camera_ready = False
            
        # Start capture thread regardless of camera status
        self.running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        
        logger.info("Camera streamer started successfully")
        return True
        
    def _capture_loop(self):
        """Main capture loop running in separate thread"""
        logger.info("Capture loop started")
        
        while self.running:
            try:
                if self.camera_ready and self.cap and self.cap.isOpened():
                    # Capture frame from camera
                    ret, frame = self.cap.read()
                    if ret and frame is not None:
                        # Resize frame to target resolution
                        frame = cv2.resize(frame, (CAMERA_WIDTH, CAMERA_HEIGHT))
                        
                        # Update queue (remove old frame if queue is full)
                        if self.frame_queue.full():
                            try:
                                self.frame_queue.get_nowait()
                            except Empty:
                                pass
                        self.frame_queue.put(frame)
                        self.last_frame_time = time.time()
                    else:
                        logger.warning("Failed to capture frame from camera")
                        self._add_black_frame()
                else:
                    # Camera not ready, add black frame
                    self._add_black_frame()
                    
            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                self._add_black_frame()
                
            # Control frame rate
            time.sleep(1.0 / CAMERA_FPS)
            
        logger.info("Capture loop stopped")
        
    def _add_black_frame(self):
        """Add black frame to queue when camera fails"""
        if not self.frame_queue.full():
            self.frame_queue.put(self.black_frame.copy())
            
    def get_frame(self):
        """Get the latest frame from the queue"""
        try:
            # Check if we have recent frames
            if time.time() - self.last_frame_time > BLACK_FRAME_DURATION:
                return self.black_frame.copy()
                
            frame = self.frame_queue.get_nowait()
            return frame
        except Empty:
            return self.black_frame.copy()
            
    def stop(self):
        """Stop the camera streamer"""
        logger.info("Stopping camera streamer...")
        self.running = False
        
        if self.capture_thread:
            self.capture_thread.join(timeout=2)
            
        if self.cap:
            self.cap.release()
            
        logger.info("Camera streamer stopped")

# Global camera streamer instance
camera_streamer = OpenCVCameraStreamer()

# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    camera_streamer.stop()
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# FastAPI app
app = FastAPI(title="EZREC Camera Streamer")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "camera_ready": camera_streamer.camera_ready,
        "queue_size": camera_streamer.frame_queue.qsize(),
        "last_frame_time": camera_streamer.last_frame_time
    }

@app.get("/live-preview")
async def live_preview():
    """Stream MJPEG video"""
    def generate_frames():
        while True:
            try:
                frame = camera_streamer.get_frame()
                
                # Encode frame as JPEG
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if not ret:
                    continue
                    
                # Create MJPEG frame
                frame_data = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n'
                       b'Content-Length: ' + str(len(frame_data)).encode() + b'\r\n'
                       b'\r\n' + frame_data + b'\r\n')
                       
            except Exception as e:
                logger.error(f"Error generating frame: {e}")
                time.sleep(0.1)
                
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/status")
async def status():
    """Detailed status endpoint"""
    return {
        "camera_ready": camera_streamer.camera_ready,
        "running": camera_streamer.running,
        "queue_size": camera_streamer.frame_queue.qsize(),
        "last_frame_time": camera_streamer.last_frame_time,
        "uptime": time.time() - camera_streamer.last_frame_time if camera_streamer.last_frame_time > 0 else 0
    }

@app.get("/camera-status")
async def camera_status():
    """Health check endpoint for camera status"""
    try:
        # Check if camera is working
        if camera_streamer.camera_ready and camera_streamer.cap and camera_streamer.cap.isOpened():
            # Try to capture a test frame
            ret, frame = camera_streamer.cap.read()
            if ret and frame is not None:
                return {
                    "status": "healthy",
                    "camera_ready": True,
                    "frame_available": True,
                    "frame_size": f"{frame.shape[1]}x{frame.shape[0]}",
                    "queue_size": camera_streamer.frame_queue.qsize(),
                    "last_frame_age": time.time() - camera_streamer.last_frame_time
                }
            else:
                return {
                    "status": "degraded",
                    "camera_ready": True,
                    "frame_available": False,
                    "message": "Camera opened but no frames available"
                }
        else:
            return {
                "status": "unhealthy",
                "camera_ready": False,
                "frame_available": False,
                "message": "Camera not initialized or not ready"
            }
    except Exception as e:
        return {
            "status": "error",
            "camera_ready": False,
            "frame_available": False,
            "error": str(e)
        }

def main():
    """Main function"""
    logger.info("Starting EZREC OpenCV Camera Streamer...")
    
    # Start camera streamer
    if not camera_streamer.start():
        logger.error("Failed to start camera streamer")
        sys.exit(1)
        
    # Start FastAPI server
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=9000,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        camera_streamer.stop()
        logger.info("Camera streamer shutdown complete")

if __name__ == "__main__":
    main() 