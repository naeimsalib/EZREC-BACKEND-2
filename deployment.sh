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
    mkdir -p $PROJECT_DIR/{temp,logs}
    
    print_success "Project directory created: $PROJECT_DIR"
}

# Copy project files
copy_project_files() {
    print_status "Copying project files..."
    
    # Copy all Python files
    cp *.py $PROJECT_DIR/ 2>/dev/null || true
    cp requirements.txt $PROJECT_DIR/ 2>/dev/null || true
    cp env.example $PROJECT_DIR/ 2>/dev/null || true
    
    # Set permissions
    chmod +x $PROJECT_DIR/*.py
    
    print_success "Project files copied"
}

# Setup Python virtual environment
setup_virtual_environment() {
    print_status "Setting up Python virtual environment..."
    
    cd $PROJECT_DIR
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install Python packages
    pip install -r requirements.txt
    
    print_success "Virtual environment setup completed"
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

# Install systemd service
install_systemd_service() {
    print_status "Installing systemd service..."
    
    # Check if service file exists
    if [ ! -f "${SERVICE_NAME}.service" ]; then
        print_error "Service file ${SERVICE_NAME}.service not found in $(pwd). Please make sure it exists."
        exit 1
    fi
    # Copy service file
    sudo cp ${SERVICE_NAME}.service /etc/systemd/system/
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable ${SERVICE_NAME}
    
    print_success "Systemd service installed and enabled"
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
    echo "4. Start the service: sudo systemctl start ${SERVICE_NAME}"
    echo "5. Check service status: sudo systemctl status ${SERVICE_NAME}"
    echo "6. View logs: sudo journalctl -u ${SERVICE_NAME} -f"
    echo
    print_status "Service management commands:"
    echo "• Start:   sudo systemctl start ${SERVICE_NAME}"
    echo "• Stop:    sudo systemctl stop ${SERVICE_NAME}"
    echo "• Restart: sudo systemctl restart ${SERVICE_NAME}"
    echo "• Status:  sudo systemctl status ${SERVICE_NAME}"
    echo "• Logs:    sudo journalctl -u ${SERVICE_NAME} -f"
    echo
    print_warning "A reboot may be required for camera changes to take effect"
}

# Main deployment function
main() {
    check_root
    
    print_status "Starting EZREC Backend deployment on Raspberry Pi"
    
    cleanup_old_installation
    update_system
    install_system_packages
    setup_project_directory
    copy_project_files
    setup_virtual_environment
    setup_environment
    setup_camera_permissions
    install_systemd_service
    test_camera
    
    display_final_instructions
}

# Run main function
main "$@" 