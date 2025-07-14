#!/usr/bin/env python3
"""
EZREC Camera Streamer Service
- Owns the camera (Picamera2 or OpenCV)
- Streams MJPEG on port 9000
- Accepts START_RECORD/STOP_RECORD commands on port 9999
- Reads resolution/FPS/camera device from .env or auto-detects
"""
import os
import threading
import time
import socket
import cv2
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv

load_dotenv("/opt/ezrec-backend/.env")

RESOLUTION = os.getenv("RESOLUTION", "1280x720")
RECORDING_FPS = int(os.getenv("RECORDING_FPS", "30"))
CAMERA_DEVICE = os.getenv("CAMERA_DEVICE")

# Auto-detect camera device if not set
if not CAMERA_DEVICE:
    for i in range(4):
        dev = f"/dev/video{i}"
        if os.path.exists(dev):
            CAMERA_DEVICE = dev
            break
    else:
        CAMERA_DEVICE = 0  # fallback to default

width, height = map(int, RESOLUTION.lower().split('x'))

class CameraStreamer:
    def __init__(self):
        self.cap = cv2.VideoCapture(CAMERA_DEVICE)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, RECORDING_FPS)
        self.frame = None
        self.recording = False
        self.video_writer = None
        self.lock = threading.Lock()
        self.running = True

    def start(self):
        threading.Thread(target=self.capture_loop, daemon=True).start()
        threading.Thread(target=self.command_server, daemon=True).start()
        self.http_server()

    def capture_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            with self.lock:
                self.frame = frame.copy()
                if self.recording and self.video_writer:
                    self.video_writer.write(frame)
            time.sleep(1/RECORDING_FPS)

    def command_server(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('localhost', 9999))
        s.listen(1)
        while self.running:
            conn, _ = s.accept()
            data = conn.recv(1024).decode()
            if data.startswith("START"):
                filename = data.split(" ")[1].strip()
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                self.video_writer = cv2.VideoWriter(filename, fourcc, RECORDING_FPS, (width, height))
                self.recording = True
                conn.sendall(b'OK\n')
            elif data.startswith("STOP"):
                self.recording = False
                if self.video_writer:
                    self.video_writer.release()
                    self.video_writer = None
                conn.sendall(b'OK\n')
            conn.close()

    def http_server(self):
        class StreamHandler(BaseHTTPRequestHandler):
            def do_GET(inner_self):
                inner_self.send_response(200)
                inner_self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
                inner_self.end_headers()
                while True:
                    with self.lock:
                        if self.frame is None:
                            continue
                        ret, jpeg = cv2.imencode('.jpg', self.frame)
                        if not ret:
                            continue
                        inner_self.wfile.write(b'--frame\r\n')
                        inner_self.wfile.write(b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                    time.sleep(1/RECORDING_FPS)
        HTTPServer(('0.0.0.0', 9000), StreamHandler).serve_forever()

if __name__ == "__main__":
    CameraStreamer().start() 