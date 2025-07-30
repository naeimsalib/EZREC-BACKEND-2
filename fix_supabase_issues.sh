#!/bin/bash

echo "🔧 Fixing Supabase integration issues..."
echo "========================================"

# Check .env file
echo "📄 Checking .env file..."
if [ -f "/opt/ezrec-backend/.env" ]; then
    echo "✅ .env file exists"
    echo "📋 Current .env content:"
    cat /opt/ezrec-backend/.env | grep -E "(SUPABASE|AWS)" || echo "⚠️ No Supabase/AWS keys found"
    echo ""
    echo "⚠️ IMPORTANT: Your .env file has been preserved!"
    echo "⚠️ No modifications will be made to your existing .env file."
else
    echo "❌ .env file not found"
    echo "📝 Please create your .env file manually:"
    echo "   sudo nano /opt/ezrec-backend/.env"
    echo ""
    echo "📋 Required variables:"
    echo "   SUPABASE_URL=your_supabase_url"
    echo "   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key"
    echo "   USER_ID=your_user_id"
    echo "   CAMERA_ID=your_camera_id"
fi

# Fix missing update_booking_status function in API
echo "🔧 Fixing missing update_booking_status function..."
API_FILE="/opt/ezrec-backend/api/api_server.py"

if [ -f "$API_FILE" ]; then
    # Check if update_booking_status is imported
    if ! grep -q "from booking_utils import update_booking_status" "$API_FILE"; then
        echo "📝 Adding missing import to API server..."
        # Add import at the top of the file
        sudo sed -i '1i from booking_utils import update_booking_status' "$API_FILE"
        echo "✅ Added update_booking_status import"
    else
        echo "✅ update_booking_status import already exists"
    fi
else
    echo "❌ API server file not found"
fi

# Check if booking_utils.py exists and has the function
echo "📄 Checking booking_utils.py..."
if [ -f "/opt/ezrec-backend/api/booking_utils.py" ]; then
    if grep -q "def update_booking_status" "/opt/ezrec-backend/api/booking_utils.py"; then
        echo "✅ update_booking_status function exists in booking_utils.py"
    else
        echo "❌ update_booking_status function missing from booking_utils.py"
        echo "📝 Adding function to booking_utils.py..."
        sudo -u ezrec tee -a /opt/ezrec-backend/api/booking_utils.py > /dev/null << 'EOF'

def update_booking_status(booking_id: str, new_status: str) -> bool:
    """Update booking status in Supabase"""
    try:
        from supabase import create_client, Client
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not supabase_url or not supabase_key:
            print("⚠️ Supabase credentials not configured")
            return False
            
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Update the booking status
        result = supabase.table('bookings').update({
            'status': new_status,
            'updated_at': 'now()'
        }).eq('id', booking_id).execute()
        
        print(f"✅ Updated booking {booking_id} status to {new_status}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to update booking status: {e}")
        return False
EOF
        echo "✅ Added update_booking_status function"
    fi
else
    echo "❌ booking_utils.py not found"
fi

# Restart API service to apply changes
echo "🔄 Restarting API service..."
sudo systemctl restart ezrec-api.service

# Wait a moment and check status
sleep 3
echo "📊 API service status:"
sudo systemctl status ezrec-api.service --no-pager -l

echo "✅ Supabase issues fix completed" 