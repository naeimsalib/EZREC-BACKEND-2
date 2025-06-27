#!/bin/bash

# EZREC Backend Deployment Script for Raspberry Pi
# This script installs and configures the EZREC backend system

set -e

echo "🚀 Starting EZREC Backend Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/opt/ezrec-backend"
SERVICE_NAME="ezrec-backend"
USER=$(whoami)

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root for some operations
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root. Run as pi user instead."
        exit 1
    fi
}

# Clean up old installations
cleanup_old_installation() {
    print_status "Cleaning up old installations..."
    
    # Stop and disable old service
    sudo systemctl stop ${SERVICE_NAME} 2>/dev/null || true
    sudo systemctl disable ${SERVICE_NAME} 2>/dev/null || true
    
    # Kill any existing camera processes
    sudo pkill -f "ezrec" 2>/dev/null || true
    sudo pkill -f "picamera" 2>/dev/null || true
    sudo pkill -f "camera" 2>/dev/null || true
    
    # Remove old service file
    sudo rm -f /etc/systemd/system/${SERVICE_NAME}.service
    
    # Backup and remove old installation
    if [ -d "$PROJECT_DIR" ]; then
        print_warning "Found existing installation at $PROJECT_DIR"
        sudo rm -rf ${PROJECT_DIR}.backup 2>/dev/null || true
        sudo mv $PROJECT_DIR ${PROJECT_DIR}.backup 2>/dev/null || true
        print_success "Old installation backed up to ${PROJECT_DIR}.backup"
    fi
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    print_success "Cleanup completed"
}

# Update system packages
update_system() {
    print_status "Updating system packages..."
    sudo apt-get update
    sudo apt-get upgrade -y
    print_success "System updated"
}

# Install required system packages
install_system_packages() {
    print_status "Installing required system packages..."
    
    # Essential packages
    sudo apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        git \
        ffmpeg \
        v4l-utils \
        python3-dev \
        libffi-dev \
        libssl-dev \
        build-essential
    
    # Raspberry Pi specific packages
    sudo apt-get install -y \
        python3-picamera2 \
        python3-libcamera \
        libcamera-apps \
        libcamera-dev
    
    print_success "System packages installed"
}

# Create project directory and set permissions
setup_project_directory() {
    print_status "Setting up project directory..."
    
    sudo mkdir -p $PROJECT_DIR
    sudo chown -R $USER:$USER $PROJECT_DIR
    
    # Create subdirectories
    mkdir -p $PROJECT_DIR/{temp,logs,raw_recordings,processed_recordings,media_cache}
    
    print_success "Project directory created: $PROJECT_DIR"
}

# Copy project files
copy_project_files() {
    print_status "Copying project files..."
    
    # Copy all Python files
    cp *.py $PROJECT_DIR/ 2>/dev/null || true
    cp requirements.txt $PROJECT_DIR/ 2>/dev/null || true
    cp env.example $PROJECT_DIR/ 2>/dev/null || true
    
    # Copy log_collector.py if present
    if [ -f "$HOME/EZREC-BACKEND-2/log_collector.py" ]; then
        cp $HOME/EZREC-BACKEND-2/log_collector.py $PROJECT_DIR/
    fi
    
    # Set permissions
    chmod +x $PROJECT_DIR/*.py
    
    print_success "Project files copied"
}

# Setup environment configuration
setup_environment() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        cp $PROJECT_DIR/env.example $PROJECT_DIR/.env
        print_warning "Environment file created at $PROJECT_DIR/.env"
        print_warning "Please edit this file with your Supabase credentials and camera ID"
    else
        print_success "Environment file already exists"
    fi
}

# Install Python dependencies in venv
install_python_deps() {
    print_status "Setting up Python virtual environment..."
    if [ ! -d "$PROJECT_DIR/venv" ]; then
        python3 -m venv $PROJECT_DIR/venv
    fi
    source $PROJECT_DIR/venv/bin/activate
    pip install --upgrade pip
    pip install -r $PROJECT_DIR/requirements.txt
    deactivate
    print_success "Python dependencies installed in venv."
}

# Backup and restore .env
backup_env() {
    if [ -f "$PROJECT_DIR/.env" ]; then
        cp $PROJECT_DIR/.env $PROJECT_DIR/.env.bak
        print_status ".env backed up to .env.bak"
    fi
}
restore_env() {
    if [ -f "$PROJECT_DIR/.env.bak" ]; then
        cp $PROJECT_DIR/.env.bak $PROJECT_DIR/.env
        print_status ".env restored from .env.bak"
    fi
}

# Validate .env for required keys
validate_env() {
    REQUIRED_KEYS=(SUPABASE_URL SUPABASE_KEY CAMERA_ID)
    for key in "${REQUIRED_KEYS[@]}"; do
        if ! grep -q "^$key=" $PROJECT_DIR/.env; then
            print_error ".env missing required key: $key"
            exit 1
        fi
    done
    print_success ".env validation passed."
}

# Print FFmpeg and picamera2 versions
print_versions() {
    print_status "FFmpeg version:"; ffmpeg -version | head -n 1
    print_status "picamera2 version:"; python3 -c "import picamera2; print(picamera2.__version__)" 2>/dev/null || echo "picamera2 not installed"
}

# Create systemd service files for all microservices
create_service_files() {
    print_status "Creating/updating systemd service files..."
    SVC_USER="$USER"
    SVC_DIR="/etc/systemd/system"
    # booking_sync
    sudo tee $SVC_DIR/booking_sync.service > /dev/null <<EOF
[Unit]
Description=EZREC Booking Sync Service
After=network.target

[Service]
Type=simple
User=$SVC_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python3 $PROJECT_DIR/booking_sync.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    # recorder
    sudo tee $SVC_DIR/recorder.service > /dev/null <<EOF
[Unit]
Description=EZREC Recorder Service
After=network.target

[Service]
Type=simple
User=$SVC_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python3 $PROJECT_DIR/recorder.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    # video_worker
    sudo tee $SVC_DIR/video_worker.service > /dev/null <<EOF
[Unit]
Description=EZREC Video Worker Service
After=network.target

[Service]
Type=simple
User=$SVC_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python3 $PROJECT_DIR/video_worker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    # system_status
    sudo tee $SVC_DIR/system_status.service > /dev/null <<EOF
[Unit]
Description=EZREC System Status Service
After=network.target

[Service]
Type=simple
User=$SVC_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python3 $PROJECT_DIR/system_status.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    # log_collector
    sudo tee $SVC_DIR/log_collector.service > /dev/null <<EOF
[Unit]
Description=EZREC Log Collector Service
After=network.target

[Service]
Type=simple
User=$SVC_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python3 $PROJECT_DIR/log_collector.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    print_success "All systemd service files created/updated."
}

# Install systemd services for all microservices and log_collector
install_systemd_services() {
    print_status "Enabling and reloading systemd services..."
    for svc in booking_sync recorder video_worker system_status log_collector; do
        sudo systemctl enable $svc
    done
    sudo systemctl daemon-reload
    print_success "All systemd services enabled and systemd reloaded."
}

# Setup camera permissions
setup_camera_permissions() {
    print_status "Setting up camera permissions..."
    
    # Add user to video group
    sudo usermod -a -G video $USER
    
    # Set camera permissions
    sudo chmod 666 /dev/video* 2>/dev/null || true
    
    # Enable camera if on Raspberry Pi
    if [ -f /boot/config.txt ]; then
        if ! grep -q "camera_auto_detect=1" /boot/config.txt; then
            echo "camera_auto_detect=1" | sudo tee -a /boot/config.txt
        fi
        if ! grep -q "dtoverlay=vc4-kms-v3d" /boot/config.txt; then
            echo "dtoverlay=vc4-kms-v3d" | sudo tee -a /boot/config.txt
        fi
    fi
    
    print_success "Camera permissions configured"
}

# Test camera connectivity
test_camera() {
    print_status "Testing camera connectivity..."
    
    if command -v libcamera-hello &> /dev/null; then
        if timeout 5 libcamera-hello --list-cameras &> /dev/null; then
            print_success "Camera detected successfully"
        else
            print_warning "Camera not detected or not accessible"
        fi
    else
        print_warning "libcamera-hello not available for testing"
    fi
}

# Display final instructions
display_final_instructions() {
    print_success "🎉 EZREC Backend deployment completed!"
    echo
    print_status "Next steps:"
    echo "1. Edit the environment file: nano $PROJECT_DIR/.env"
    echo "2. Add your Supabase URL and key"
    echo "3. Set your camera ID"
    echo "4. Start all services:"
    echo "   sudo systemctl start booking_sync"
    echo "   sudo systemctl start recorder"
    echo "   sudo systemctl start video_worker"
    echo "   sudo systemctl start system_status"
    echo "   sudo systemctl start log_collector"
    echo "5. Check service status:"
    echo "   sudo systemctl status booking_sync"
    echo "   sudo systemctl status recorder"
    echo "   sudo systemctl status video_worker"
    echo "   sudo systemctl status system_status"
    echo "   sudo systemctl status log_collector"
    echo "6. View logs:"
    echo "   sudo journalctl -u booking_sync -f"
    echo "   sudo journalctl -u recorder -f"
    echo "   sudo journalctl -u video_worker -f"
    echo "   sudo journalctl -u system_status -f"
    echo "   sudo journalctl -u log_collector -f"
    echo
    print_status "Service management commands (replace <service> with one of: booking_sync, recorder, video_worker, system_status, log_collector):"
    echo "• Start:   sudo systemctl start <service>"
    echo "• Stop:    sudo systemctl stop <service>"
    echo "• Restart: sudo systemctl restart <service>"
    echo "• Status:  sudo systemctl status <service>"
    echo "• Logs:    sudo journalctl -u <service> -f"
    echo
    print_warning "A reboot may be required for camera changes to take effect"
}

# After copying project files, fix venv ownership and install requirements
fix_venv_and_install_requirements() {
    print_status "Fixing venv ownership and installing Python dependencies in venv..."
    sudo chown -R $USER:$USER $PROJECT_DIR
    source $PROJECT_DIR/venv/bin/activate
    pip install --upgrade pip
    pip install -r $PROJECT_DIR/requirements.txt
    deactivate
    print_success "Python dependencies installed in venv and ownership fixed."
}

# Main deployment function
main() {
    check_root
    
    print_status "Starting EZREC Backend deployment on Raspberry Pi"
    
    backup_env
    cleanup_old_installation
    update_system
    install_system_packages
    setup_project_directory
    copy_project_files
    setup_environment
    setup_camera_permissions
    install_python_deps
    fix_venv_and_install_requirements
    create_service_files
    install_systemd_services
    test_camera
    restore_env
    validate_env
    print_versions
    print_warning "If you are using ezrec_backend.py, disable recorder.py in systemd to avoid parallel recorders."
    display_final_instructions
}

# Run main function
main "$@" 