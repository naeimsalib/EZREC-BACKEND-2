#!/usr/bin/env python3
"""
EZREC Camera Streamer Service (robust picamera2 version)
- Owns the camera (Picamera2)
- Streams MJPEG on port 9000
- Accepts START <filename>/STOP commands on port 9999
- Thread-safe, robust, and production-ready
"""
import os
import threading
import time
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
import numpy as np
import cv2
import logging
from queue import Queue, Empty
import io
from PIL import Image, ImageDraw, ImageFont
import sys
import traceback

load_dotenv("/opt/ezrec-backend/.env")

RESOLUTION = os.getenv("RESOLUTION", "1280x720")
RECORDING_FPS = int(os.getenv("RECORDING_FPS", "30"))
width, height = map(int, RESOLUTION.lower().split('x'))
# Allow more simultaneous MJPEG clients (default 10, can override in .env)
MAX_MJPEG_CLIENTS = int(os.getenv("MAX_MJPEG_CLIENTS", "10"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("camera_streamer")

class CameraStreamer:
    def __init__(self):
        self.picam2 = Picamera2()
        self.config = self.picam2.create_video_configuration(
            main={"size": (width, height), "format": "RGB888"},
            controls={"FrameRate": RECORDING_FPS}
        )
        self.picam2.configure(self.config)
        self.frame_queue = Queue(maxsize=2)  # Thread-safe buffer for latest frame
        self.recording = False
        self.recording_filename = None
        self.lock = threading.Lock()
        self.running = True
        self.mjpeg_clients = set()
        self.mjpeg_clients_lock = threading.Lock()
        self.last_frame = None
        self.placeholder_jpeg = self.generate_placeholder_jpeg()

    def generate_placeholder_jpeg(self):
        # Generate a simple 'Recording in Progress' JPEG
        img = Image.new('RGB', (width, height), color=(30, 30, 30))
        draw = ImageDraw.Draw(img)
        text = "RECORDING IN PROGRESS"
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        except Exception:
            font = ImageFont.load_default()
        textwidth, textheight = draw.textsize(text, font=font)
        x = (width - textwidth) // 2
        y = (height - textheight) // 2
        draw.text((x, y), text, font=font, fill=(255, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        return buf.getvalue()

    def start(self):
        try:
            self.picam2.start()
        except Exception as e:
            logger.error(f"Failed to start camera: {e}")
            traceback.print_exc()
            sys.exit(1)
        threading.Thread(target=self.capture_loop, daemon=True).start()
        threading.Thread(target=self.command_server, daemon=True).start()
        self.http_server()

    def capture_loop(self):
        while self.running:
            try:
                frame = self.picam2.capture_array()
                self.last_frame = frame
                # Always keep only the latest frame in the queue
                while not self.frame_queue.empty():
                    try:
                        self.frame_queue.get_nowait()
                    except Empty:
                        break
                self.frame_queue.put(frame, block=False)
            except Exception as e:
                logger.error(f"Capture loop error: {e}")
                traceback.print_exc()
            time.sleep(1/RECORDING_FPS)

    def command_server(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('localhost', 9999))
        s.listen(1)
        logger.info("Command server listening on port 9999")
        while self.running:
            try:
                conn, _ = s.accept()
                data = conn.recv(1024).decode()
                if data.startswith("START"):
                    filename = data.split(" ")[1].strip()
                    with self.lock:
                        if not self.recording:
                            encoder = H264Encoder()
                            self.picam2.start_recording(encoder, filename)
                            self.recording = True
                            self.recording_filename = filename
                            logger.info(f"Started recording: {filename}")
                    conn.sendall(b'OK\n')
                elif data.startswith("STOP"):
                    with self.lock:
                        if self.recording:
                            try:
                                self.picam2.stop_recording()
                                logger.info(f"Stopped recording: {self.recording_filename}")
                            except Exception as e:
                                logger.error(f"Error stopping recording: {e}")
                            self.recording = False
                            self.recording_filename = None
                    conn.sendall(b'OK\n')
                else:
                    conn.sendall(b'ERR\n')
                conn.close()
            except Exception as e:
                logger.error(f"Command server error: {e}")

    def http_server(self):
        streamer = self
        class StreamHandler(BaseHTTPRequestHandler):
            def do_GET(inner_self):
                # Limit number of clients
                with streamer.mjpeg_clients_lock:
                    if len(streamer.mjpeg_clients) >= MAX_MJPEG_CLIENTS:
                        inner_self.send_response(503)
                        inner_self.end_headers()
                        return
                    client_id = id(inner_self)
                    streamer.mjpeg_clients.add(client_id)
                try:
                    inner_self.send_response(200)
                    inner_self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
                    inner_self.end_headers()
                    while True:
                        try:
                            with streamer.lock:
                                if streamer.recording and streamer.last_frame is not None:
                                    # If recording, serve placeholder
                                    jpeg_bytes = streamer.placeholder_jpeg
                                else:
                                    frame = streamer.frame_queue.get(timeout=2)
                                    ret, jpeg = cv2.imencode('.jpg', frame)
                                    if not ret:
                                        logger.warning("MJPEG handler: Failed to encode frame as JPEG")
                                        continue
                                    jpeg_bytes = jpeg.tobytes()
                        except Empty:
                            logger.warning("MJPEG handler: No frame available in queue")
                            continue
                        try:
                            inner_self.wfile.write(b'--frame\r\n')
                            inner_self.wfile.write(b'Content-Type: image/jpeg\r\n\r\n' + jpeg_bytes + b'\r\n')
                        except (ConnectionResetError, BrokenPipeError):
                            logger.info("MJPEG client disconnected")
                            break
                        except Exception as e:
                            logger.error(f"MJPEG stream error: {e}")
                            break
                        time.sleep(1/RECORDING_FPS)
                finally:
                    with streamer.mjpeg_clients_lock:
                        streamer.mjpeg_clients.discard(client_id)
        logger.info("MJPEG HTTP server listening on port 9000")
        HTTPServer(('0.0.0.0', 9000), StreamHandler).serve_forever()

if __name__ == "__main__":
    CameraStreamer().start() 