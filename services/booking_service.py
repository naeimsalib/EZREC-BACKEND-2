#!/usr/bin/env python3
"""
EZREC Booking Service
Handles all booking operations and management
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import pytz

# Add config to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.settings import settings, get_logger, get_database_client

logger = get_logger(__name__)

class BookingService:
    """Service for booking operations and management"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.bookings_file = settings.paths.bookings_path / "bookings.json"
        self._ensure_bookings_file()
    
    def _ensure_bookings_file(self):
        """Ensure bookings file exists"""
        self.bookings_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.bookings_file.exists():
            self._save_bookings([])
    
    def _load_bookings(self) -> List[Dict[str, Any]]:
        """Load bookings from local file"""
        try:
            if self.bookings_file.exists():
                with open(self.bookings_file, 'r') as f:
                    bookings = json.load(f)
                self.logger.info(f"📋 Loaded {len(bookings)} bookings from cache")
                return bookings
            else:
                self.logger.warning("⚠️ No bookings file found")
                return []
        except Exception as e:
            self.logger.error(f"❌ Failed to load bookings: {e}")
            return []
    
    def _save_bookings(self, bookings: List[Dict[str, Any]]):
        """Save bookings to local file"""
        try:
            with open(self.bookings_file, 'w') as f:
                json.dump(bookings, f, indent=2)
            self.logger.info(f"💾 Saved {len(bookings)} bookings to cache")
        except Exception as e:
            self.logger.error(f"❌ Failed to save bookings: {e}")
    
    def find_active_booking(self) -> Optional[Dict[str, Any]]:
        """Find an active booking that should be recording now"""
        bookings = self._load_bookings()
        if not bookings:
            return None
        
        now = datetime.now(pytz.timezone('America/New_York'))
        self.logger.info(f"🔍 Checking {len(bookings)} bookings at {now}")
        
        for booking in bookings:
            try:
                start_time = datetime.fromisoformat(booking['start_time'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(booking['end_time'].replace('Z', '+00:00'))
                
                self.logger.info(f"🔍 Booking {booking['id']}: {start_time} - {end_time}")
                self.logger.info(f"   Now: {now}")
                
                if start_time <= now <= end_time:
                    self.logger.info(f"🎯 Active booking found: {booking['id']}")
                    return booking
            except Exception as e:
                self.logger.error(f"❌ Error parsing booking {booking.get('id', 'unknown')}: {e}")
                continue
        
        self.logger.info("❌ No active booking found")
        return None
    
    def create_booking(self, booking_data: Dict[str, Any]) -> Optional[str]:
        """Create a new booking"""
        try:
            # Add timestamps
            now = datetime.now(pytz.timezone('America/New_York'))
            booking_data.update({
                'created_at': now.isoformat(),
                'updated_at': now.isoformat()
            })
            
            # Save to local file
            bookings = self._load_bookings()
            bookings.append(booking_data)
            self._save_bookings(bookings)
            
            # Try to save to Supabase
            try:
                supabase = get_database_client()
                result = supabase.table("bookings").insert(booking_data).execute()
                if result.data:
                    self.logger.info(f"✅ Created booking {booking_data['id']} in Supabase")
                else:
                    self.logger.warning(f"⚠️ Failed to create booking {booking_data['id']} in Supabase")
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to sync booking to Supabase: {e}")
            
            self.logger.info(f"✅ Created booking: {booking_data['id']}")
            return booking_data['id']
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create booking: {e}")
            return None
    
    def update_booking_status(self, booking_id: str, status: str) -> bool:
        """Update booking status"""
        try:
            # Update local file
            bookings = self._load_bookings()
            for booking in bookings:
                if booking['id'] == booking_id:
                    booking['status'] = status
                    booking['updated_at'] = datetime.now(pytz.timezone('America/New_York')).isoformat()
                    break
            self._save_bookings(bookings)
            
            # Try to update Supabase
            try:
                supabase = get_database_client()
                result = supabase.table("bookings").update({
                    "status": status,
                    "updated_at": "now()"
                }).eq("id", booking_id).execute()
                
                if result.data:
                    self.logger.info(f"✅ Updated booking {booking_id} status to {status} in Supabase")
                else:
                    self.logger.warning(f"⚠️ Failed to update booking {booking_id} in Supabase")
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to sync booking status to Supabase: {e}")
            
            self.logger.info(f"✅ Updated booking {booking_id} status to {status}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to update booking {booking_id} status: {e}")
            return False
    
    def get_booking_by_id(self, booking_id: str) -> Optional[Dict[str, Any]]:
        """Get booking by ID"""
        try:
            bookings = self._load_bookings()
            for booking in bookings:
                if booking['id'] == booking_id:
                    return booking
            return None
        except Exception as e:
            self.logger.error(f"❌ Failed to get booking {booking_id}: {e}")
            return None
    
    def get_all_bookings(self) -> List[Dict[str, Any]]:
        """Get all bookings"""
        return self._load_bookings()
    
    def delete_booking(self, booking_id: str) -> bool:
        """Delete a booking"""
        try:
            bookings = self._load_bookings()
            bookings = [b for b in bookings if b['id'] != booking_id]
            self._save_bookings(bookings)
            
            # Try to delete from Supabase
            try:
                supabase = get_database_client()
                result = supabase.table("bookings").delete().eq("id", booking_id).execute()
                if result.data:
                    self.logger.info(f"✅ Deleted booking {booking_id} from Supabase")
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to delete booking from Supabase: {e}")
            
            self.logger.info(f"✅ Deleted booking: {booking_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to delete booking {booking_id}: {e}")
            return False
    
    def cleanup_expired_bookings(self, days_old: int = 7) -> int:
        """Clean up expired bookings older than specified days"""
        try:
            cutoff_date = datetime.now(pytz.timezone('America/New_York')) - timedelta(days=days_old)
            bookings = self._load_bookings()
            
            original_count = len(bookings)
            bookings = [
                b for b in bookings 
                if datetime.fromisoformat(b.get('created_at', '1970-01-01').replace('Z', '+00:00')) > cutoff_date
            ]
            
            if len(bookings) < original_count:
                self._save_bookings(bookings)
                cleaned_count = original_count - len(bookings)
                self.logger.info(f"🧹 Cleaned up {cleaned_count} expired bookings")
                return cleaned_count
            
            return 0
            
        except Exception as e:
            self.logger.error(f"❌ Failed to cleanup expired bookings: {e}")
            return 0
