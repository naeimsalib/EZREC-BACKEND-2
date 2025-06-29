#!/bin/bash

# EZREC Backend Deployment Script for Raspberry Pi
# This script installs and configures the EZREC backend system

set -e

# Lock File or Idempotency Protection
LOCK_FILE="/tmp/ezrec_deploy.lock"
if [ -f "$LOCK_FILE" ]; then
  print_error "Deployment already running. Remove $LOCK_FILE to retry."
  exit 1
fi
trap "rm -f $LOCK_FILE" EXIT
touch "$LOCK_FILE"

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
print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_root() {
  if [[ $EUID -eq 0 ]]; then
    print_error "Do not run this script as root."
    exit 1
  fi
}

cleanup_old_installation() {
  print_status "Cleaning up old installations..."
  for svc in booking_sync recorder video_worker system_status log_collector; do
    sudo systemctl stop $svc 2>/dev/null || true
    sudo systemctl disable $svc 2>/dev/null || true
    sudo rm -f /etc/systemd/system/$svc.service
  done
  sudo pkill -f "ezrec|picamera|camera" 2>/dev/null || true
  [ -d "$PROJECT_DIR" ] && sudo mv "$PROJECT_DIR" "${PROJECT_DIR}.backup" || true
  sudo systemctl daemon-reload
  print_success "Cleanup complete"
}

update_system() {
  print_status "Updating system packages..."
  sudo apt-get update
  sudo apt-get upgrade -y
  print_success "System packages updated"
}

install_system_packages() {
  print_status "Installing required packages..."
  sudo apt-get install -y python3 python3-pip python3-venv git ffmpeg v4l-utils \
    python3-dev libffi-dev libssl-dev build-essential \
    python3-picamera2 python3-libcamera libcamera-apps libcamera-dev
  print_success "System packages installed"
}

setup_project_directory() {
  print_status "Setting up project directory..."
  sudo mkdir -p "$PROJECT_DIR"
  sudo chown -R "$USER:$USER" "$PROJECT_DIR"
  mkdir -p "$PROJECT_DIR"/{temp,logs,raw_recordings,processed_recordings,media_cache,backend}
  print_success "Project directory ready"
}

copy_project_files() {
  print_status "Copying project files..."
  rsync -av --delete backend/ "$PROJECT_DIR/backend/"
  cp requirements.txt "$PROJECT_DIR"/ 2>/dev/null || true
  cp env.example "$PROJECT_DIR"/ 2>/dev/null || true
  chmod +x "$PROJECT_DIR/backend"/*.py
  print_success "Project files copied"
}

setup_camera_permissions() {
  print_status "Setting camera permissions..."
  sudo usermod -a -G video "$USER"
  sudo chmod 666 /dev/video* 2>/dev/null || true
  sudo sed -i '/^camera_auto_detect=/d' /boot/config.txt
  sudo sed -i '/^dtoverlay=vc4-kms-v3d/d' /boot/config.txt
  echo "camera_auto_detect=1" | sudo tee -a /boot/config.txt
  echo "dtoverlay=vc4-kms-v3d" | sudo tee -a /boot/config.txt
  print_success "Camera permissions set"
}

install_python_deps() {
  print_status "Installing Python dependencies..."
  python3 -m venv "$PROJECT_DIR/venv"
  source "$PROJECT_DIR/venv/bin/activate"
  pip install --upgrade pip
  pip install -r "$PROJECT_DIR/requirements.txt"
  deactivate
  print_success "Python dependencies installed"
}

fix_venv_ownership() {
  sudo chown -R "$USER:$USER" "$PROJECT_DIR"
}

ensure_dotenv_absolute_path() {
  print_status "Ensuring absolute path to .env..."
  for script in "$PROJECT_DIR"/*.py; do
    sed -i 's/load_dotenv()/load_dotenv("\/opt\/ezrec-backend\/.env")/g' "$script"
  done
  print_success ".env paths updated"
}

setup_systemd_services() {
  print_status "Copying systemd service files..."
  sudo cp "$PROJECT_DIR/systemd"/*.service /etc/systemd/system/
  sudo systemctl daemon-reload
  print_success "Systemd service files copied and systemd reloaded"
}

enable_services() {
  print_status "Enabling services..."
  for svc in booking_sync recorder video_worker system_status log_collector health_api; do
    sudo systemctl enable "$svc"
  done
  print_success "Services enabled"
}

# Start and verify services after enabling
start_and_verify_services() {
    print_status "Starting services..."
    for svc in booking_sync recorder video_worker system_status log_collector; do
        sudo systemctl restart "$svc"
        sleep 2
        if systemctl is-active --quiet "$svc"; then
            print_success "$svc started successfully"
        else
            print_error "$svc failed to start"
            sudo journalctl -u "$svc" --no-pager | tail -n 10
        fi
    done
}

print_versions() {
  print_status "FFmpeg version: $(ffmpeg -version | head -n1)"
  print_status "picamera2 version: $(python3 -c 'import picamera2; print(picamera2.__version__)' 2>/dev/null || echo 'Not installed')"
}

test_camera() {
  print_status "Testing camera..."
  if command -v libcamera-hello &>/dev/null; then
    if timeout 5 libcamera-hello --list-cameras &>/dev/null; then
      print_success "Camera detected"
    else
      print_warning "Camera not detected"
    fi
  else
    print_warning "libcamera-hello not installed"
  fi
}

display_final_instructions() {
  echo -e "\n🎉 ${GREEN}EZREC Backend is ready!${NC}"
  echo -e "${BLUE}[INFO]${NC} Start services:"
  echo "  sudo systemctl start booking_sync recorder video_worker system_status log_collector"
  echo -e "${BLUE}[INFO]${NC} View logs:"
  echo "  sudo journalctl -u recorder -f"
  echo -e "${YELLOW}[NOTE]${NC} A reboot may be required for camera changes."
}

main() {
  check_root
  cleanup_old_installation
  update_system
  install_system_packages
  setup_project_directory
  copy_project_files
  setup_camera_permissions
  install_python_deps
  fix_venv_ownership
  ensure_dotenv_absolute_path
  setup_systemd_services
  enable_services
  start_and_verify_services
  test_camera
  print_versions
  # Automated log rotation for journald
  print_status "Configuring journald log rotation..."
  sudo tee /etc/systemd/journald.conf.d/ezrec.conf > /dev/null <<EOF
[Journal]
SystemMaxUse=100M
SystemKeepFree=20M
MaxRetentionSec=3d
EOF
  sudo systemctl restart systemd-journald
  print_success "Journald log rotation configured"
  display_final_instructions
  # ---
  # Health Endpoint & Sentry/Slack Notifier (suggestion):
  # Consider writing system_status.json from system_status.py and serving it via Flask/FastAPI for a health dashboard.
  # For error notifications, integrate Sentry or Slack webhook in log_collector.py or other services.
}

main "$@"
