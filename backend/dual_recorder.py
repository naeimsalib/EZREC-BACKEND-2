#!/usr/bin/env python3
"""
EZREC Dual Camera Recorder Service
Uses the new service architecture for clean separation of concerns
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import services and utilities
from services.camera_service import CameraService
from services.booking_service import BookingService
from utils.logger import setup_service_logging
from utils.exceptions import handle_exception

# Set up logging
logger = setup_service_logging("dual_recorder")

class DualRecorderService:
    """Main dual recorder service using the new architecture"""
    
    def __init__(self):
        self.camera_service = CameraService()
        self.booking_service = BookingService()
        self.current_booking = None
        logger.info("🎥 Dual Recorder Service initialized")
    
    @handle_exception
    def start_recording_for_booking(self, booking: dict) -> bool:
        """Start recording for a specific booking"""
        try:
            logger.info(f"🎬 Starting recording for booking: {booking['id']}")
            
            # Update booking status
            self.booking_service.update_booking_status(booking['id'], 'recording')
            
            # Start recording session
            success = self.camera_service.start_recording_session(booking['id'])
            
            if success:
                self.current_booking = booking
                logger.info("✅ Recording started successfully")
                return True
            else:
                self.booking_service.update_booking_status(booking['id'], 'failed')
                logger.error("❌ Failed to start recording")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error starting recording: {e}")
            self.booking_service.update_booking_status(booking['id'], 'failed')
            return False
    
    @handle_exception
    def stop_recording(self):
        """Stop current recording session"""
        if not self.camera_service.is_recording():
            return
        
        logger.info("🛑 Stopping recording session")
        
        # Stop camera recording
        self.camera_service.stop_recording_session()
        
        # Update booking status
        if self.current_booking:
            self.booking_service.update_booking_status(self.current_booking['id'], 'completed')
            self.current_booking = None
        
        logger.info("✅ Recording stopped")
    
    @handle_exception
    def check_and_handle_bookings(self):
        """Check for active bookings and handle recording"""
        # Find active booking
        active_booking = self.booking_service.find_active_booking()
        
        if active_booking and not self.camera_service.is_recording():
            # Start recording for active booking
            self.start_recording_for_booking(active_booking)
        elif not active_booking and self.camera_service.is_recording():
            # Stop recording if no active booking
            self.stop_recording()
    
    def get_status(self) -> dict:
        """Get current service status"""
        return {
            'recording': self.camera_service.is_recording(),
            'current_booking': self.current_booking['id'] if self.current_booking else None,
            'camera_status': self.camera_service.get_recording_status()
        }

def main():
    """Main service function - runs continuously"""
    logger.info("🎥 EZREC Dual Recorder Service Starting")
    
    # Create service
    recorder = DualRecorderService()
    
    try:
        while True:
            # Check and handle bookings
            recorder.check_and_handle_bookings()
            
            # Wait before checking again
            time.sleep(5)
            
    except KeyboardInterrupt:
        logger.info("🛑 Service interrupted by user")
        if recorder.camera_service.is_recording():
            recorder.stop_recording()
    except Exception as e:
        logger.error(f"❌ Service error: {e}")
        if recorder.camera_service.is_recording():
            recorder.stop_recording()

if __name__ == "__main__":
    main()
