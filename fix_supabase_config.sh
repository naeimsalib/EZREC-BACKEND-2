#!/bin/bash

echo "🔧 Fixing Supabase configuration..."
echo "==================================="

# Check if .env file exists and has proper values
echo "📄 Checking .env file..."
if [ -f "/opt/ezrec-backend/.env" ]; then
    echo "✅ .env file exists"
    
    # Check if Supabase keys are properly set
    SUPABASE_URL=$(grep "^SUPABASE_URL=" /opt/ezrec-backend/.env | cut -d'=' -f2)
    SUPABASE_KEY=$(grep "^SUPABASE_SERVICE_ROLE_KEY=" /opt/ezrec-backend/.env | cut -d'=' -f2)
    
    if [ "$SUPABASE_URL" = "your_supabase_url_here" ] || [ -z "$SUPABASE_URL" ]; then
        echo "❌ SUPABASE_URL not properly configured"
        echo "📝 Please update your .env file with actual Supabase credentials"
        echo "   You can get these from your Supabase project dashboard"
    else
        echo "✅ SUPABASE_URL is configured"
    fi
    
    if [ "$SUPABASE_KEY" = "your_supabase_service_role_key_here" ] || [ -z "$SUPABASE_KEY" ]; then
        echo "❌ SUPABASE_SERVICE_ROLE_KEY not properly configured"
        echo "📝 Please update your .env file with actual Supabase credentials"
    else
        echo "✅ SUPABASE_SERVICE_ROLE_KEY is configured"
    fi
else
    echo "❌ .env file not found"
fi

# Make booking_utils.py more robust to handle missing Supabase credentials
echo "🔧 Making booking_utils.py more robust..."
cat > /opt/ezrec-backend/api/booking_utils.py << 'EOF'
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
                        bookings = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    bookings = []
                
                # Update the booking
                for booking in bookings:
                    if booking.get('id') == booking_id:
                        booking['status'] = new_status
                        break
                
                with open(bookings_file, 'w') as f:
                    json.dump(bookings, f, indent=2)
                
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
                        return json.load(f)
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
                    bookings = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                bookings = []
            
            bookings.append(booking_data)
            
            with open(bookings_file, 'w') as f:
                json.dump(bookings, f, indent=2)
            
            print(f"✅ Created booking locally")
            return True
    except Exception as e:
        print(f"❌ Error creating booking: {e}")
        return False
EOF

# Set proper permissions
sudo chown ezrec:ezrec /opt/ezrec-backend/api/booking_utils.py
sudo chmod 644 /opt/ezrec-backend/api/booking_utils.py

echo "✅ Supabase configuration fix completed"
echo ""
echo "📋 Next steps:"
echo "1. Update your .env file with actual Supabase credentials"
echo "2. Restart the API service: sudo systemctl restart ezrec-api.service"
echo "3. Test the API: curl http://localhost:8000/status" 