#!/usr/bin/env python3
"""
Debug API Server
Add debug prints to see where API server is failing
"""

import subprocess
import sys

def main():
    print("🔍 DEBUG API SERVER")
    print("="*50)
    
    # Create a debug version of the API server with print statements
    debug_code = '''
#!/usr/bin/env python3
print("🚀 DEBUG: Starting API server...")

try:
    print("📥 DEBUG: Importing modules...")
    from supabase import create_client
    print("✅ DEBUG: supabase imported")
    from fastapi import FastAPI, HTTPException, Query, Request, Body, Header, Depends
    print("✅ DEBUG: fastapi imported")
    from fastapi.middleware.cors import CORSMiddleware
    print("✅ DEBUG: CORSMiddleware imported")
    from pydantic import BaseModel, EmailStr
    print("✅ DEBUG: pydantic imported")
    from typing import List, Optional
    print("✅ DEBUG: typing imported")
    from pathlib import Path
    print("✅ DEBUG: pathlib imported")
    from datetime import datetime, timedelta, timezone
    print("✅ DEBUG: datetime imported")
    import json
    print("✅ DEBUG: json imported")
    import logging
    print("✅ DEBUG: logging imported")
    import boto3
    print("✅ DEBUG: boto3 imported")
    import os
    print("✅ DEBUG: os imported")
    from dotenv import load_dotenv
    print("✅ DEBUG: dotenv imported")
    from urllib.parse import unquote
    print("✅ DEBUG: urllib imported")
    import sys
    print("✅ DEBUG: sys imported")
    from fastapi.templating import Jinja2Templates
    print("✅ DEBUG: Jinja2Templates imported")
    from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse, PlainTextResponse
    print("✅ DEBUG: responses imported")
    import urllib.parse
    print("✅ DEBUG: urllib.parse imported")
    import requests
    print("✅ DEBUG: requests imported")
    import shutil
    print("✅ DEBUG: shutil imported")
    from uuid import uuid4
    print("✅ DEBUG: uuid imported")
    import smtplib
    print("✅ DEBUG: smtplib imported")
    from email.message import EmailMessage
    print("✅ DEBUG: EmailMessage imported")
    import psutil
    print("✅ DEBUG: psutil imported")
    import time
    print("✅ DEBUG: time imported")
    import numpy as np
    print("✅ DEBUG: numpy imported")
    try:
        from picamera2 import Picamera2
        PICAMERA2_AVAILABLE = True
        print("✅ DEBUG: picamera2 imported")
    except ImportError:
        import cv2
        PICAMERA2_AVAILABLE = False
        print("✅ DEBUG: cv2 imported (picamera2 not available)")
    import io
    print("✅ DEBUG: io imported")
    import threading
    print("✅ DEBUG: threading imported")
    import pytz
    print("✅ DEBUG: pytz imported")
    
    print("📁 DEBUG: Loading .env file...")
    # --------------------------
    # LOAD .env FILE
    # --------------------------
    load_dotenv(dotenv_path="/opt/ezrec-backend/.env")
    print("✅ DEBUG: .env file loaded")
    
    print("📝 DEBUG: Setting up logging...")
    # --------------------------
    # LOGGING SETUP
    # --------------------------
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    logger = logging.getLogger("EZREC")
    print("✅ DEBUG: Logging setup complete")
    
    print("🔧 DEBUG: Setting up Supabase...")
    # --------------------------
    # SUPABASE CONFIGURATION
    # --------------------------
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    print(f"🔍 DEBUG: SUPABASE_URL exists: {SUPABASE_URL is not None}")
    print(f"🔍 DEBUG: SUPABASE_KEY exists: {SUPABASE_KEY is not None}")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
    print("✅ DEBUG: Supabase client created")
    
    print("🚀 DEBUG: Creating FastAPI app...")
    # --------------------------
    # FASTAPI INIT
    # --------------------------
    app = FastAPI()
    print("✅ DEBUG: FastAPI app created")
    
    @app.get("/test-alive")
    def test_alive():
        return {"status": "alive"}
    
    print("🌐 DEBUG: Adding CORS middleware...")
    # Allow only the production frontend domain for CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://d3p0722z34ceid.cloudfront.net",
            "http://localhost:3000",
            "http://127.0.0.1:3000"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
    print("✅ DEBUG: CORS middleware added")
    
    print("📁 DEBUG: Setting up file paths...")
    # --------------------------
    # FILE PATHS
    # --------------------------
    BOOKINGS_FILE = Path("/opt/ezrec-backend/api/local_data/bookings.json")
    SYSTEM_FILE = Path("/opt/ezrec-backend/api/local_data/system.json")
    RECORDINGS_DIR = Path("/opt/ezrec-backend/recordings")
    print("✅ DEBUG: File paths set")
    
    print("☁️ DEBUG: Setting up S3...")
    # --------------------------
    # S3 CONFIGURATION
    # --------------------------
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET = os.getenv("AWS_S3_BUCKET", "ezrec-videos")
    USER_MEDIA_BUCKET = os.getenv("AWS_USER_MEDIA_BUCKET", S3_BUCKET)
    print("✅ DEBUG: S3 configuration set")
    
    s3 = boto3.client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    print("✅ DEBUG: S3 client created")
    
    print("📋 DEBUG: Setting up models...")
    # --------------------------
    # MODELS
    # --------------------------
    class Booking(BaseModel):
        id: str
        user_id: str
        start_time: str
        end_time: str
        date: str
        camera_id: Optional[str] = None
        recording_id: Optional[str] = None
        booking_id: str
        email: Optional[str] = None
    
    class SystemSettings(BaseModel):
        main_logo_path: str
        sponsor_logo_paths: List[str]
        intro_video_path: str
    
    class DeletePayload(BaseModel):
        key: str
    
    class MediaNotifyRequest(BaseModel):
        user_id: str
        action: str  # "upload" or "delete"
        s3_key: str
        filename: str
        media_type: str
    
    class ShareRequest(BaseModel):
        key: str
        user_id: str  # Now required
    
    class ShareResponse(BaseModel):
        url: str
    
    class SendShareEmailRequest(BaseModel):
        email: EmailStr
        link: str
        videoId: str
    
    class RevokeShareRequest(BaseModel):
        user_id: str
    print("✅ DEBUG: Models defined")
    
    print("🔗 DEBUG: Setting up endpoints...")
    # --------------------------
    # ENDPOINTS
    # --------------------------
    @app.get("/")
    def root():
        return {"message": "EZREC FastAPI is running"}
    
    @app.get("/status")
    def status():
        return {"status": "online", "time": datetime.utcnow().isoformat()}
    
    @app.get("/camera-status")
    def camera_status():
        return {"status": "camera_ready", "streaming": True}
    
    print("✅ DEBUG: Basic endpoints defined")
    
    print("🚀 DEBUG: Starting uvicorn server...")
    # --------------------------
    # SERVER STARTUP
    # --------------------------
    if __name__ == "__main__":
        import uvicorn
        logger.info("🚀 Starting EZREC API Server on port 9000...")
        print("🎯 DEBUG: About to start uvicorn server...")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=9000,
            log_level="info",
            access_log=True
        )
        print("🎯 DEBUG: uvicorn.run() completed")
    
    print("✅ DEBUG: API server setup complete")
    
except Exception as e:
    print(f"❌ DEBUG: Error during setup: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("🎯 DEBUG: Script completed successfully")
'''
    
    # Write debug version to temporary file
    debug_file = "/tmp/debug_api_server.py"
    with open(debug_file, 'w') as f:
        f.write(debug_code)
    
    print(f"📝 DEBUG: Created debug API server at {debug_file}")
    
    # Run the debug version with shorter timeout to see output
    print("\n🚀 DEBUG: Running debug API server...")
    try:
        result = subprocess.run([
            "/opt/ezrec-backend/api/venv/bin/python3", 
            debug_file
        ], 
        cwd="/opt/ezrec-backend/api",
        capture_output=True,
        text=True,
        timeout=10  # Shorter timeout to see output
        )
        
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"Output:\n{result.stdout}")
        if result.stderr:
            print(f"Error:\n{result.stderr}")
            
        if result.returncode == 0:
            print("✅ DEBUG: API server completed successfully")
        else:
            print(f"❌ DEBUG: API server failed with exit code {result.returncode}")
            
    except subprocess.TimeoutExpired:
        print("✅ DEBUG: API server is running (timeout reached)")
        print("This means the server started successfully and is running continuously!")
    except Exception as e:
        print(f"❌ DEBUG: Error running API server: {e}")
    
    # Clean up
    import os
    if os.path.exists(debug_file):
        os.remove(debug_file)
        print(f"🧹 DEBUG: Cleaned up {debug_file}")

if __name__ == "__main__":
    main() 