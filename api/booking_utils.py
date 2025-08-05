#!/usr/bin/env python3
"""
EZREC Booking Utilities
Provides functions for updating booking status in Supabase
"""

import os
import logging
from typing import Optional
from supabase import create_client

# Configure logging
logger = logging.getLogger("booking_utils")

def update_booking_status(booking_id: str, status: str) -> bool:
    """
    Update booking status in Supabase
    
    Args:
        booking_id: The booking ID to update
        status: The new status (e.g., 'completed', 'failed', 'processing')
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get Supabase credentials
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            logger.warning("⚠️ Supabase credentials not configured")
            return False
        
        # Initialize Supabase client
        supabase = create_client(supabase_url, supabase_key)
        
        # Update the booking status
        result = supabase.table("bookings").update({
            "status": status,
            "updated_at": "now()"
        }).eq("id", booking_id).execute()
        
        if result.data:
            logger.info(f"✅ Updated booking {booking_id} status to {status}")
            return True
        else:
            logger.warning(f"⚠️ No booking found with ID {booking_id}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to update booking {booking_id} status: {e}")
        return False

def get_booking_by_id(booking_id: str) -> Optional[dict]:
    """
    Get booking details by ID
    
    Args:
        booking_id: The booking ID to retrieve
    
    Returns:
        dict: Booking data or None if not found
    """
    try:
        # Get Supabase credentials
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            logger.warning("⚠️ Supabase credentials not configured")
            return None
        
        # Initialize Supabase client
        supabase = create_client(supabase_url, supabase_key)
        
        # Get the booking
        result = supabase.table("bookings").select("*").eq("id", booking_id).single().execute()
        
        if result.data:
            return result.data
        else:
            logger.warning(f"⚠️ No booking found with ID {booking_id}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Failed to get booking {booking_id}: {e}")
        return None

def create_booking(booking_data: dict) -> Optional[str]:
    """
    Create a new booking in Supabase
    
    Args:
        booking_data: Dictionary containing booking information
    
    Returns:
        str: Booking ID if successful, None otherwise
    """
    try:
        # Get Supabase credentials
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            logger.warning("⚠️ Supabase credentials not configured")
            return None
        
        # Initialize Supabase client
        supabase = create_client(supabase_url, supabase_key)
        
        # Create the booking
        result = supabase.table("bookings").insert(booking_data).execute()
        
        if result.data:
            booking_id = result.data[0].get("id")
            logger.info(f"✅ Created booking {booking_id}")
            return booking_id
        else:
            logger.error("❌ Failed to create booking")
            return None
            
    except Exception as e:
        logger.error(f"❌ Failed to create booking: {e}")
        return None
