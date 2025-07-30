import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from supabase import create_client, Client
from supabase._sync.client import SupabaseException

# Load environment variables
SUPABASE_URL = os.getenv('SUPABASE_URL', 'your_supabase_url_here')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', 'your_supabase_service_role_key_here')

# Initialize Supabase client with error handling
supabase: Optional[Client] = None
try:
    if SUPABASE_URL != 'your_supabase_url_here' and SUPABASE_KEY != 'your_supabase_service_role_key_here':
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase client initialized successfully")
    else:
        print("⚠️ Supabase credentials not configured, using local mode")
except Exception as e:
    print(f"⚠️ Failed to initialize Supabase client: {e}")
    print("⚠️ System will work in local mode only")

BOOKING_CACHE_FILE = Path("/opt/ezrec-backend/api/local_data/bookings.json")

def update_booking_status(booking_id: str, new_status: str) -> bool:
    """Update booking status in Supabase or local storage"""
    try:
        if supabase:
            # Update in Supabase
            response = supabase.table('bookings').update(
                {'status': new_status}
            ).eq('id', booking_id).execute()
            print(f"✅ Updated booking {booking_id} status to {new_status} in Supabase")
            return True
        else:
            # Update local file
            bookings_file = Path('/opt/ezrec-backend/api/local_data/bookings.json')
            if bookings_file.exists():
                try:
                    with open(bookings_file, 'r') as f:
                        data = json.load(f)
                        # Handle both list and dict formats
                        if isinstance(data, dict) and 'bookings' in data:
                            bookings = data['bookings']
                        elif isinstance(data, list):
                            bookings = data
                        else:
                            bookings = []
                except (json.JSONDecodeError, FileNotFoundError):
                    bookings = []
                
                # Update the booking
                for booking in bookings:
                    if booking.get('id') == booking_id:
                        booking['status'] = new_status
                        break
                
                # Save back in the same format
                if isinstance(data, dict) and 'bookings' in data:
                    data['bookings'] = bookings
                    save_data = data
                else:
                    save_data = bookings
                
                with open(bookings_file, 'w') as f:
                    json.dump(save_data, f, indent=2)
                
                print(f"✅ Updated booking {booking_id} status to {new_status} locally")
                return True
            else:
                print(f"❌ Could not update booking {booking_id}: no local storage")
                return False
    except Exception as e:
        print(f"❌ Error updating booking status: {e}")
        return False

def get_bookings() -> list:
    """Get bookings from Supabase or local storage"""
    try:
        if supabase:
            # Get from Supabase
            response = supabase.table('bookings').select('*').execute()
            return response.data
        else:
            # Get from local file
            bookings_file = Path('/opt/ezrec-backend/api/local_data/bookings.json')
            if bookings_file.exists():
                try:
                    with open(bookings_file, 'r') as f:
                        data = json.load(f)
                        # Handle both list and dict formats
                        if isinstance(data, dict) and 'bookings' in data:
                            return data['bookings']
                        elif isinstance(data, list):
                            return data
                        else:
                            return []
                except (json.JSONDecodeError, FileNotFoundError):
                    return []
            return []
    except Exception as e:
        print(f"❌ Error getting bookings: {e}")
        return []

def create_booking(booking_data: Dict[str, Any]) -> bool:
    """Create booking in Supabase or local storage"""
    try:
        if supabase:
            # Create in Supabase
            response = supabase.table('bookings').insert(booking_data).execute()
            print(f"✅ Created booking in Supabase")
            return True
        else:
            # Create in local file
            bookings_file = Path('/opt/ezrec-backend/api/local_data/bookings.json')
            try:
                with open(bookings_file, 'r') as f:
                    data = json.load(f)
                    # Handle both list and dict formats
                    if isinstance(data, dict) and 'bookings' in data:
                        bookings = data['bookings']
                        is_dict_format = True
                    elif isinstance(data, list):
                        bookings = data
                        is_dict_format = False
                    else:
                        bookings = []
                        is_dict_format = False
            except (json.JSONDecodeError, FileNotFoundError):
                bookings = []
                is_dict_format = False
            
            # Add the new booking
            bookings.append(booking_data)
            
            # Save back in the same format
            if is_dict_format:
                data['bookings'] = bookings
                save_data = data
            else:
                save_data = bookings
            
            with open(bookings_file, 'w') as f:
                json.dump(save_data, f, indent=2)
            
            print(f"✅ Created booking locally")
            return True
    except Exception as e:
        print(f"❌ Error creating booking: {e}")
        return False
