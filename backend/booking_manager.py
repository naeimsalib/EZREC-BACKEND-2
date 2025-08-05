#!/usr/bin/env python3
"""
Enhanced Booking Manager with Status Tracking
- Manages bookings with real-time status updates
- Provides retry logic for failed operations
- Syncs status with frontend in real-time
- Handles booking reconciliation between Pi and Supabase
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import pytz

# Add API directory to path
API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../api'))
if API_DIR not in sys.path:
    sys.path.append(API_DIR)

from booking_utils import update_booking_status

class BookingStatus(Enum):
    SCHEDULED = "scheduled"
    RECORDING = "recording"
    PROCESSING = "processing"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class CameraStatus:
    left: bool = False
    right: bool = False
    left_error: Optional[str] = None
    right_error: Optional[str] = None
    left_file_size: int = 0
    right_file_size: int = 0

@dataclass
class EnhancedBooking:
    id: str
    user_id: str
    camera_id: str
    start_time: str
    end_time: str
    status: BookingStatus = BookingStatus.SCHEDULED
    camera_status: CameraStatus = None
    created_at: str = None
    updated_at: str = None
    recording_start: Optional[str] = None
    recording_end: Optional[str] = None
    merge_status: Optional[str] = None
    upload_status: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.camera_status is None:
            self.camera_status = CameraStatus()
        if self.created_at is None:
            self.created_at = datetime.now(pytz.timezone('America/New_York')).isoformat()
        self.updated_at = datetime.now(pytz.timezone('America/New_York')).isoformat()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['status'] = self.status.value
        data['camera_status'] = asdict(self.camera_status)
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'EnhancedBooking':
        """Create from dictionary"""
        if 'camera_status' in data and isinstance(data['camera_status'], dict):
            data['camera_status'] = CameraStatus(**data['camera_status'])
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = BookingStatus(data['status'])
        return cls(**data)

class BookingManager:
    """Manages enhanced bookings with status tracking and retry logic"""
    
    def __init__(self, cache_file: Path, user_id: str, camera_id: str):
        self.cache_file = cache_file
        self.user_id = user_id
        self.camera_id = camera_id
        self.logger = logging.getLogger(__name__)
        
        # Ensure cache file exists
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.cache_file.exists():
            self._save_bookings([])
    
    def _load_bookings(self) -> List[EnhancedBooking]:
        """Load bookings from cache file"""
        try:
            with open(self.cache_file, 'r') as f:
                data = json.load(f)
            
            # Handle both old and new formats
            if isinstance(data, list):
                # Old format - convert to new format
                bookings = []
                for item in data:
                    booking = EnhancedBooking(
                        id=item.get('id', item.get('booking_id', 'unknown')),
                        user_id=item.get('user_id', self.user_id),
                        camera_id=item.get('camera_id', self.camera_id),
                        start_time=item.get('start_time'),
                        end_time=item.get('end_time'),
                        status=BookingStatus.SCHEDULED
                    )
                    bookings.append(booking)
                return bookings
            elif isinstance(data, dict) and 'bookings' in data:
                # New format
                return [EnhancedBooking.from_dict(b) for b in data['bookings']]
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to load bookings: {e}")
            return []
    
    def _save_bookings(self, bookings: List[EnhancedBooking]):
        """Save bookings to cache file"""
        try:
            data = {
                'bookings': [booking.to_dict() for booking in bookings],
                'last_updated': datetime.now(pytz.timezone('America/New_York')).isoformat(),
                'user_id': self.user_id,
                'camera_id': self.camera_id
            }
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save bookings: {e}")
    
    def get_active_booking(self) -> Optional[EnhancedBooking]:
        """Get the currently active booking"""
        now = datetime.now(pytz.timezone('America/New_York'))  # Make timezone-aware
        bookings = self._load_bookings()
        
        for booking in bookings:
            try:
                start_time = datetime.fromisoformat(booking.start_time.replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(booking.end_time.replace('Z', '+00:00'))
                
                if (booking.user_id == self.user_id and 
                    booking.camera_id == self.camera_id and 
                    start_time <= now <= end_time):
                    return booking
            except Exception as e:
                self.logger.warning(f"Error parsing booking times: {e}")
                continue
        
        return None
    
    def update_booking_status(self, booking_id: str, status: BookingStatus, 
                            error_message: Optional[str] = None,
                            camera_status: Optional[CameraStatus] = None):
        """Update booking status and sync with Supabase"""
        bookings = self._load_bookings()
        
        for booking in bookings:
            if booking.id == booking_id:
                booking.status = status
                booking.updated_at = datetime.now(pytz.timezone('America/New_York')).isoformat()
                
                if error_message:
                    booking.error_message = error_message
                
                if camera_status:
                    booking.camera_status = camera_status
                
                # Update recording timestamps
                if status == BookingStatus.RECORDING and not booking.recording_start:
                    booking.recording_start = datetime.now(pytz.timezone('America/New_York')).isoformat()
                elif status in [BookingStatus.COMPLETED, BookingStatus.FAILED] and not booking.recording_end:
                    booking.recording_end = datetime.now(pytz.timezone('America/New_York')).isoformat()
                
                # Handle retry logic
                if status == BookingStatus.FAILED:
                    booking.retry_count += 1
                    if booking.retry_count < booking.max_retries:
                        self.logger.info(f"Booking {booking_id} failed, retry {booking.retry_count}/{booking.max_retries}")
                        booking.status = BookingStatus.SCHEDULED
                        booking.error_message = None
                
                self._save_bookings(bookings)
                
                # Sync with Supabase
                try:
                    update_booking_status(booking_id, status.value)
                    self.logger.info(f"Updated booking {booking_id} status to {status.value}")
                except Exception as e:
                    self.logger.error(f"Failed to sync booking status with Supabase: {e}")
                
                break
    
    def add_booking(self, booking_data: dict) -> EnhancedBooking:
        """Add a new booking"""
        booking = EnhancedBooking(
            id=booking_data.get('id', booking_data.get('booking_id')),
            user_id=booking_data.get('user_id', self.user_id),
            camera_id=booking_data.get('camera_id', self.camera_id),
            start_time=booking_data.get('start_time'),
            end_time=booking_data.get('end_time')
        )
        
        bookings = self._load_bookings()
        bookings.append(booking)
        self._save_bookings(bookings)
        
        self.logger.info(f"Added new booking: {booking.id}")
        return booking
    
    def remove_booking(self, booking_id: str):
        """Remove a booking"""
        bookings = self._load_bookings()
        bookings = [b for b in bookings if b.id != booking_id]
        self._save_bookings(bookings)
        
        self.logger.info(f"Removed booking: {booking_id}")
    
    def get_failed_bookings(self) -> List[EnhancedBooking]:
        """Get bookings that have failed and can be retried"""
        bookings = self._load_bookings()
        return [b for b in bookings if b.status == BookingStatus.FAILED and b.retry_count < b.max_retries]
    
    def cleanup_old_bookings(self, days_to_keep: int = 7):
        """Remove old completed/failed bookings"""
        cutoff_date = datetime.now(pytz.timezone('America/New_York')) - timedelta(days=days_to_keep)
        bookings = self._load_bookings()
        
        original_count = len(bookings)
        bookings = [b for b in bookings if (
            b.status not in [BookingStatus.COMPLETED, BookingStatus.FAILED] or
            datetime.fromisoformat(b.updated_at.replace('Z', '+00:00')) > cutoff_date
        )]
        
        if len(bookings) < original_count:
            self._save_bookings(bookings)
            self.logger.info(f"Cleaned up {original_count - len(bookings)} old bookings")
    
    def get_booking_stats(self) -> dict:
        """Get booking statistics"""
        bookings = self._load_bookings()
        
        stats = {
            'total': len(bookings),
            'scheduled': len([b for b in bookings if b.status == BookingStatus.SCHEDULED]),
            'recording': len([b for b in bookings if b.status == BookingStatus.RECORDING]),
            'processing': len([b for b in bookings if b.status == BookingStatus.PROCESSING]),
            'uploading': len([b for b in bookings if b.status == BookingStatus.UPLOADING]),
            'completed': len([b for b in bookings if b.status == BookingStatus.COMPLETED]),
            'failed': len([b for b in bookings if b.status == BookingStatus.FAILED]),
            'cancelled': len([b for b in bookings if b.status == BookingStatus.CANCELLED])
        }
        
        return stats

def create_test_booking(user_id: str, camera_id: str, duration_minutes: int = 2) -> EnhancedBooking:
    """Create a test booking for debugging"""
    now = datetime.now(pytz.timezone('America/New_York'))
    start_time = now + timedelta(seconds=30)  # Start in 30 seconds
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    booking_data = {
        'id': f'test-{int(time.time())}',
        'user_id': user_id,
        'camera_id': camera_id,
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat()
    }
    
    return EnhancedBooking(**booking_data)

if __name__ == "__main__":
    # Test the booking manager
    import os
    from dotenv import load_dotenv
    
    load_dotenv("/opt/ezrec-backend/.env")
    
    user_id = os.getenv('USER_ID', 'test-user')
    camera_id = os.getenv('CAMERA_ID', 'test-camera')
    cache_file = Path("/opt/ezrec-backend/api/local_data/bookings.json")
    
    manager = BookingManager(cache_file, user_id, camera_id)
    
    # Create a test booking
    test_booking = create_test_booking(user_id, camera_id)
    manager.add_booking(test_booking.__dict__)
    
    print(f"✅ Created test booking: {test_booking.id}")
    print(f"   Start: {test_booking.start_time}")
    print(f"   End: {test_booking.end_time}")
    print(f"   Status: {test_booking.status.value}")
    
    # Show stats
    stats = manager.get_booking_stats()
    print(f"📊 Booking stats: {stats}") 