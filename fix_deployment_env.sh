#!/bin/bash

echo "🔧 Fixing deployment script to preserve .env files..."
echo "=================================================="

# Backup the current deployment script
echo "📋 Backing up current deployment script..."
sudo cp /opt/ezrec-backend/deployment.sh /opt/ezrec-backend/deployment.sh.backup

# Create a patch to fix the .env handling
echo "🔧 Creating .env preservation patch..."

# Find the line numbers where .env is created/overwritten
ENV_START_LINE=$(grep -n "SETUP ENVIRONMENT CONFIGURATION" /opt/ezrec-backend/deployment.sh | cut -d: -f1)
ENV_END_LINE=$(grep -n "INSTALL SYSTEMD SERVICE FILES" /opt/ezrec-backend/deployment.sh | cut -d: -f1)

echo "📍 Found .env section at lines $ENV_START_LINE to $ENV_END_LINE"

# Create a new deployment script that preserves .env
echo "🔧 Creating new deployment script with .env preservation..."

# Read the deployment script and modify the .env section
awk -v start="$ENV_START_LINE" -v end="$ENV_END_LINE" '
BEGIN { in_env_section = 0; skip_section = 0; }
{
    if (NR == start) {
        in_env_section = 1;
        skip_section = 1;
        print "#------------------------------#";
        print "# 10. SETUP ENVIRONMENT CONFIGURATION (PRESERVED)";
        print "#------------------------------#";
        print "echo \"⚙️ Checking environment configuration...\"";
        print "";
        print "ENV_FILE=\"/opt/ezrec-backend/.env\"";
        print "";
        print "# Check if .env file exists";
        print "if [ -f \"$ENV_FILE\" ]; then";
        print "    echo \"✅ .env file already exists - PRESERVING EXISTING CONFIGURATION\"";
        print "    echo \"📋 Current .env variables:\"";
        print "    grep -E \"^(SUPABASE|AWS|CAMERA|USER|EMAIL|SHARE|TIMEZONE|RECORDING)\" \"$ENV_FILE\" 2>/dev/null || echo \"⚠️ No configured variables found\"";
        print "    echo \"\"";
        print "    echo \"🔧 To modify: sudo nano /opt/ezrec-backend/.env\"";
        print "    echo \"🔧 To view: cat /opt/ezrec-backend/.env\"";
        print "else";
        print "    echo \"📝 Creating .env file from template...\"";
        print "    sudo tee \"$ENV_FILE\" > /dev/null << '\''EOF'\''";
        print "# EZREC Backend Environment Configuration";
        print "# Copy this file to .env and fill in your actual values";
        print "";
        print "# Supabase Configuration";
        print "SUPABASE_URL=your_supabase_url_here";
        print "SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here";
        print "";
        print "# AWS S3 Configuration";
        print "AWS_ACCESS_KEY_ID=your_aws_access_key_here";
        print "AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here";
        print "AWS_REGION=us-east-1";
        print "AWS_S3_BUCKET=your_s3_bucket_name_here";
        print "AWS_USER_MEDIA_BUCKET=your_user_media_bucket_here";
        print "";
        print "# Camera Configuration";
        print "CAMERA_0_SERIAL=88000";
        print "CAMERA_1_SERIAL=80000";
        print "DUAL_CAMERA_MODE=true";
        print "";
        print "# User Configuration";
        print "USER_ID=your_user_id_here";
        print "CAMERA_ID=your_camera_id_here";
        print "";
        print "# Email Configuration (for share links)";
        print "EMAIL_HOST=smtp.gmail.com";
        print "EMAIL_PORT=587";
        print "EMAIL_HOST_USER=your_email@gmail.com";
        print "EMAIL_HOST_PASSWORD=your_app_password_here";
        print "EMAIL_USE_TLS=True";
        print "EMAIL_FROM=your_email@gmail.com";
        print "";
        print "# Share Configuration";
        print "SHARE_BASE_URL=https://yourdomain.com";
        print "";
        print "# Timezone";
        print "TIMEZONE_NAME=UTC";
        print "";
        print "# Recording Configuration";
        print "RECORDING_QUALITY=high";
        print "MERGE_METHOD=side_by_side";
        print "RECORDING_FPS=30";
        print "LOG_LEVEL=INFO";
        print "BOOKING_CHECK_INTERVAL=5";
        print "EOF";
        print "    echo \"✅ Basic .env file created from template\"";
        print "    echo \"🔧 Please edit /opt/ezrec-backend/.env with your actual credentials\"";
        print "    echo \"🔧 Example: sudo nano /opt/ezrec-backend/.env\"";
        print "fi";
        print "";
        print "# Set proper permissions";
        print "sudo chown ezrec:ezrec \"$ENV_FILE\"";
        print "sudo chmod 600 \"$ENV_FILE\"";
        print "";
        print "echo \"✅ Environment configuration setup completed\"";
        next;
    }
    
    if (in_env_section && NR >= end) {
        in_env_section = 0;
        skip_section = 0;
    }
    
    if (!skip_section) {
        print;
    }
}' /opt/ezrec-backend/deployment.sh > /tmp/deployment_fixed.sh

# Replace the original deployment script
sudo cp /tmp/deployment_fixed.sh /opt/ezrec-backend/deployment.sh
sudo chmod +x /opt/ezrec-backend/deployment.sh

echo "✅ Deployment script fixed to preserve .env files"
echo ""
echo "📋 Changes made:"
echo "1. ✅ .env file will NOT be overwritten if it exists"
echo "2. ✅ Existing .env configuration will be preserved"
echo "3. ✅ Only creates .env from template if it doesn't exist"
echo "4. ✅ Shows current .env variables when file exists"
echo ""
echo "🔧 Your existing .env file is now safe from deployment script overwrites!" 