#!/usr/bin/env python3
"""
EZREC Booking Watcher Service
Monitors booking_cache.json and manages recording state transitions
"""

import os
import sys
import time
import json
import logging
import signal
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

# Add API directory to path for imports
API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../api'))
if API_DIR not in sys.path:
    sys.path.append(API_DIR)

from booking_utils import update_booking_status

# Load environment
load_dotenv("/opt/ezrec-backend/.env")

# Configuration
@dataclass
class BookingWatcherConfig:
    """Booking watcher configuration"""
    BOOKING_CACHE_FILE = Path("/opt/ezrec-backend/api/local_data/bookings.json")
    LOG_FILE = Path("/opt/ezrec-backend/logs/booking_watcher.log")
    CHECK_INTERVAL = 5  # Check every 5 seconds
    USER_ID = os.getenv('USER_ID')
    CAMERA_ID = os.getenv('CAMERA_ID')

# Setup logging
def setup_logging():
    """Setup rotating file logger"""
    from logging.handlers import RotatingFileHandler
    
    # Create log directory
    BookingWatcherConfig.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Create rotating file handler
    rotating_handler = RotatingFileHandler(
        BookingWatcherConfig.LOG_FILE,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    
    # Set formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    rotating_handler.setFormatter(formatter)
    
    # Setup logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[rotating_handler, logging.StreamHandler()]
    )
    
    return logging.getLogger(__name__)

logger = setup_logging()

class BookingState:
    """Represents the state of a booking"""
    PENDING = "PENDING"
    STARTED = "STARTED"
    ENDED = "ENDED"
    RECORDING = "RECORDING"
    RECORDING_FINISHED = "RECORDING_FINISHED"

class BookingWatcher:
    """Monitors booking cache and manages recording state transitions"""
    
    def __init__(self):
        self.current_booking = None
        self.recorder_running = False
        self.last_booking_id = None
        
        logger.info("🔍 Booking watcher initialized")
        logger.info(f"📄 Monitoring: {BookingWatcherConfig.BOOKING_CACHE_FILE}")
        logger.info(f"👤 User ID: {BookingWatcherConfig.USER_ID}")
        logger.info(f"📷 Camera ID: {BookingWatcherConfig.CAMERA_ID}")
    
    def load_bookings(self) -> list:
        """Load bookings from cache file"""
        if not BookingWatcherConfig.BOOKING_CACHE_FILE.exists():
            return []
        try:
            with open(BookingWatcherConfig.BOOKING_CACHE_FILE, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and 'bookings' in data:
                    return data['bookings']
                else:
                    return []
        except Exception as e:
            logger.error(f"❌ Error loading bookings: {e}")
            return []
    
    def get_active_booking(self, bookings: list) -> Optional[Dict[str, Any]]:
        """Get the currently active booking for this user and camera"""
        now = datetime.now()
        
        for booking in bookings:
            try:
                # Parse booking times
                start_time = datetime.fromisoformat(booking["start_time"].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(booking["end_time"].replace('Z', '+00:00'))
                
                # Check if booking matches our criteria
                user_match = booking.get("user_id") == BookingWatcherConfig.USER_ID
                camera_match = booking.get("camera_id") == BookingWatcherConfig.CAMERA_ID
                time_match = start_time <= now <= end_time
                
                if user_match and camera_match and time_match:
                    logger.info(f"✅ Found active booking: {booking.get('id', 'unknown')}")
                    logger.info(f"   Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.info(f"   End: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    return booking
                    
            except Exception as e:
                logger.error(f"❌ Error processing booking: {e}")
                continue
        
        return None
    
    def should_start_recording(self, booking: Dict[str, Any]) -> bool:
        """Check if recording should start for this booking"""
        booking_id = booking.get('id')
        
        # If no recorder is running and we have a new booking
        if not self.recorder_running and booking_id != self.last_booking_id:
            logger.info(f"🎬 Booking {booking_id} STARTED → spawning recorder")
            return True
        
        return False
    
    def should_stop_recording(self, booking: Dict[str, Any]) -> bool:
        """Check if recording should stop for this booking"""
        booking_id = booking.get('id')
        now = datetime.now()
        
        try:
            end_time = datetime.fromisoformat(booking["end_time"].replace('Z', '+00:00'))
            
            # If recorder is running and booking has ended
            if self.recorder_running and now > end_time:
                logger.info(f"🛑 Booking {booking_id} ENDED → stopping recorder")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error checking booking end time: {e}")
        
        return False
    
    def emit_start_recording_event(self, booking: Dict[str, Any]):
        """Emit start_recording event"""
        try:
            event_data = {
                "action": "start_recording",
                "booking_id": booking.get('id'),
                "user_id": booking.get('user_id'),
                "camera_id": booking.get('camera_id'),
                "start_time": booking.get('start_time'),
                "end_time": booking.get('end_time'),
                "timestamp": datetime.now().isoformat()
            }
            
            # Save event to file for dual_camera.py to pick up
            event_file = Path("/opt/ezrec-backend/recordings/start_recording.event")
            event_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(event_file, 'w') as f:
                json.dump(event_data, f, indent=2)
            
            self.recorder_running = True
            self.last_booking_id = booking.get('id')
            
            logger.info(f"📡 Emitted start_recording event for booking {booking.get('id')}")
            
            # Update booking status
            try:
                update_booking_status(booking.get('id'), BookingState.RECORDING)
                logger.info(f"📡 Updated booking status to {BookingState.RECORDING}")
            except Exception as e:
                logger.error(f"❌ Failed to update booking status: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error emitting start_recording event: {e}")
    
    def emit_stop_recording_event(self, booking: Dict[str, Any]):
        """Emit stop_recording event"""
        try:
            event_data = {
                "action": "stop_recording",
                "booking_id": booking.get('id'),
                "timestamp": datetime.now().isoformat()
            }
            
            # Save event to file for dual_camera.py to pick up
            event_file = Path("/opt/ezrec-backend/recordings/stop_recording.event")
            event_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(event_file, 'w') as f:
                json.dump(event_data, f, indent=2)
            
            self.recorder_running = False
            
            logger.info(f"📡 Emitted stop_recording event for booking {booking.get('id')}")
            
            # Update booking status
            try:
                update_booking_status(booking.get('id'), BookingState.RECORDING_FINISHED)
                logger.info(f"📡 Updated booking status to {BookingState.RECORDING_FINISHED}")
            except Exception as e:
                logger.error(f"❌ Failed to update booking status: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error emitting stop_recording event: {e}")
    
    def check_recording_complete_events(self):
        """Check for recording_complete events from dual_camera.py"""
        try:
            recordings_dir = Path("/opt/ezrec-backend/recordings")
            if not recordings_dir.exists():
                return
            
            # Look for .event files
            for event_file in recordings_dir.glob("*.event"):
                try:
                    with open(event_file, 'r') as f:
                        event_data = json.load(f)
                    
                    if event_data.get("action") == "recording_complete":
                        booking_id = event_data.get("booking_id")
                        logger.info(f"✅ Recording completed for booking {booking_id}")
                        
                        # Update booking status
                        try:
                            update_booking_status(booking_id, BookingState.RECORDING_FINISHED)
                            logger.info(f"📡 Updated booking {booking_id} status to {BookingState.RECORDING_FINISHED}")
                        except Exception as e:
                            logger.error(f"❌ Failed to update booking status: {e}")
                        
                        # Clean up event file
                        event_file.unlink()
                        
                except Exception as e:
                    logger.error(f"❌ Error processing event file {event_file}: {e}")
                    # Clean up corrupted event file
                    event_file.unlink(missing_ok=True)
                    
        except Exception as e:
            logger.error(f"❌ Error checking recording complete events: {e}")
    
    def run(self):
        """Main monitoring loop"""
        logger.info("🚀 Starting booking watcher loop")
        
        try:
            while True:
                try:
                    # Load current bookings
                    bookings = self.load_bookings()
                    logger.info(f"📋 Loaded {len(bookings)} bookings from cache")
                    
                    # Get active booking
                    active_booking = self.get_active_booking(bookings)
                    
                    if active_booking:
                        # Check if we should start recording
                        if self.should_start_recording(active_booking):
                            self.emit_start_recording_event(active_booking)
                        
                        # Check if we should stop recording
                        elif self.should_stop_recording(active_booking):
                            self.emit_stop_recording_event(active_booking)
                        
                        # Update current booking
                        self.current_booking = active_booking
                    else:
                        # No active booking
                        if self.recorder_running:
                            logger.info("⏳ No active booking found, but recorder is still running")
                        else:
                            logger.info("⏳ No active booking found, waiting...")
                        
                        self.current_booking = None
                    
                    # Check for recording complete events
                    self.check_recording_complete_events()
                    
                except Exception as e:
                    logger.error(f"❌ Error in booking watcher loop: {e}")
                    import traceback
                    logger.error(f"📋 Traceback: {traceback.format_exc()}")
                
                # Wait before next check
                time.sleep(BookingWatcherConfig.CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            logger.info("🛑 Received keyboard interrupt")
        except Exception as e:
            logger.error(f"❌ Unexpected error in booking watcher: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
        finally:
            logger.info("🛑 Booking watcher shutdown complete")

def handle_exit(sig, frame):
    """Handle graceful shutdown"""
    logger.info("🛑 Received termination signal. Exiting gracefully.")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def main():
    """Main application entry point"""
    logger.info("🚀 EZREC Booking Watcher Service started")
    logger.info(f"📄 Monitoring: {BookingWatcherConfig.BOOKING_CACHE_FILE}")
    logger.info(f"⏰ Check interval: {BookingWatcherConfig.CHECK_INTERVAL} seconds")
    
    # Validate configuration
    if not BookingWatcherConfig.USER_ID:
        logger.error("❌ USER_ID not configured in environment")
        sys.exit(1)
    
    if not BookingWatcherConfig.CAMERA_ID:
        logger.error("❌ CAMERA_ID not configured in environment")
        sys.exit(1)
    
    # Create watcher and run
    watcher = BookingWatcher()
    watcher.run()

if __name__ == "__main__":
    main() 