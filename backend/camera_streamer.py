#!/usr/bin/env python3
"""
EZREC Camera Streamer Service (picamera2 version)
- Owns the camera (Picamera2)
- Streams MJPEG on port 9000
- Accepts START <filename>/STOP commands on port 9999
- Reads resolution/FPS from .env or uses defaults
"""
import os
import threading
import time
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv
from picamera2 import Picamera2, MjpegEncoder
import numpy as np

load_dotenv("/opt/ezrec-backend/.env")

RESOLUTION = os.getenv("RESOLUTION", "1280x720")
RECORDING_FPS = int(os.getenv("RECORDING_FPS", "30"))
width, height = map(int, RESOLUTION.lower().split('x'))

class CameraStreamer:
    def __init__(self):
        self.picam2 = Picamera2()
        self.config = self.picam2.create_video_configuration(
            main={"size": (width, height), "format": "RGB888"},
            controls={"FrameRate": RECORDING_FPS}
        )
        self.picam2.configure(self.config)
        self.frame = None
        self.recording = False
        self.recording_filename = None
        self.lock = threading.Lock()
        self.running = True
        self.mjpeg_encoder = None
        self.mjpeg_stream_clients = []

    def start(self):
        self.picam2.start()
        threading.Thread(target=self.capture_loop, daemon=True).start()
        threading.Thread(target=self.command_server, daemon=True).start()
        self.http_server()

    def capture_loop(self):
        while self.running:
            frame = self.picam2.capture_array()
            with self.lock:
                self.frame = frame.copy()
            if self.recording and self.mjpeg_encoder:
                # Recording is handled by picamera2's start_recording
                pass
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
                with self.lock:
                    if not self.recording:
                        self.picam2.start_recording(filename, quality=85)
                        self.recording = True
                        self.recording_filename = filename
                conn.sendall(b'OK\n')
            elif data.startswith("STOP"):
                with self.lock:
                    if self.recording:
                        self.picam2.stop_recording()
                        self.recording = False
                        self.recording_filename = None
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
                        # Convert to JPEG
                        import cv2
                        ret, jpeg = cv2.imencode('.jpg', self.frame)
                        if not ret:
                            continue
                        inner_self.wfile.write(b'--frame\r\n')
                        inner_self.wfile.write(b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                    time.sleep(1/RECORDING_FPS)
        HTTPServer(('0.0.0.0', 9000), StreamHandler).serve_forever()

if __name__ == "__main__":
    CameraStreamer().start() 