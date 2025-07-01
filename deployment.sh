#!/bin/bash

# EZREC Backend Deployment Script (Safe for FastAPI + Cloudflare Setup)

set -e

LOCK_FILE="/tmp/ezrec_deploy.lock"
trap "rm -f $LOCK_FILE" EXIT

if [ -f "$LOCK_FILE" ]; then
  echo "[ERROR] Deployment already running. Remove $LOCK_FILE to retry."
  exit 1
fi
touch "$LOCK_FILE"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Config
PROJECT_DIR="/opt/ezrec-backend"
USER=$(whoami)

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

backup_env() {
  if [ -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env" "./env.bak"
    print_status ".env backed up to ./env.bak"
  fi
}

restore_env() {
  if [ -f "./env.bak" ]; then
    cp "./env.bak" "$PROJECT_DIR/.env"
    print_status ".env restored to project directory"
  fi
}

cleanup_old_installation() {
  print_status "Cleaning old installation..."
  backup_env

  for svc in booking_sync recorder video_worker system_status log_collector; do
    sudo systemctl stop $svc 2>/dev/null || true
    sudo systemctl disable $svc 2>/dev/null || true
    sudo rm -f /etc/systemd/system/$svc.service
  done

  sudo pkill -f "ezrec|picamera|camera" 2>/dev/null || true

  if [ -d "$PROJECT_DIR" ]; then
    sudo rm -rf "${PROJECT_DIR}.backup"
    sudo rsync -a --exclude 'api/' --exclude '.env' "$PROJECT_DIR/" "${PROJECT_DIR}.backup/"
    sudo rsync -a --delete --exclude 'api/' --exclude '.env' /dev/null/ "$PROJECT_DIR/"
  fi

  sudo systemctl daemon-reexec
  sudo systemctl daemon-reload
  print_success "Old installation cleaned, FastAPI backend preserved"
}

update_system() {
  print_status "Updating system..."
  sudo apt-get update && sudo apt-get upgrade -y
  print_success "System updated"
}

install_packages() {
  print_status "Installing system packages..."
  sudo apt-get install -y python3 python3-picamera2 python3-libcamera libcamera-apps libcamera-dev \
    python3-pip python3-venv git ffmpeg v4l-utils \
    python3-dev libffi-dev libssl-dev build-essential
  print_success "System packages installed"
}

setup_directories() {
  print_status "Setting up directories..."
  sudo mkdir -p "$PROJECT_DIR"
  sudo chown -R "$USER:$USER" "$PROJECT_DIR"
  mkdir -p "$PROJECT_DIR"/{temp,logs,raw_recordings,processed_recordings,media_cache,backend}
  restore_env
  print_success "Directories ready"
}

copy_project_files() {
  print_status "Copying project files..."
  rsync -av --delete backend/ "$PROJECT_DIR/backend/"
  cp requirements.txt "$PROJECT_DIR/" 2>/dev/null || true
  chmod +x "$PROJECT_DIR/backend"/*.py
  print_success "Files copied"
}

set_camera_permissions() {
  print_status "Setting camera permissions..."
  sudo usermod -a -G video "$USER"
  sudo chmod 666 /dev/video* /dev/v4l-subdev* 2>/dev/null || true
  sudo sed -i '/^camera_auto_detect=/d' /boot/config.txt
  sudo sed -i '/^dtoverlay=vc4-kms-v3d/d' /boot/config.txt
  echo "camera_auto_detect=1" | sudo tee -a /boot/config.txt
  echo "dtoverlay=vc4-kms-v3d" | sudo tee -a /boot/config.txt
  print_success "Camera access patched"
}

install_python_deps() {
  print_status "Installing Python dependencies..."
  python3 -m venv --system-site-packages "$PROJECT_DIR/venv"
  source "$PROJECT_DIR/venv/bin/activate"
  pip install --upgrade pip
  pip install -r "$PROJECT_DIR/requirements.txt"
  deactivate
  print_success "Python packages installed"
}

patch_systemd_services() {
  print_status "Copying and patching systemd services..."
  sudo cp "$PWD/systemd"/*.service /etc/systemd/system/
  sudo sed -i '/^DevicePolicy=/d' /etc/systemd/system/recorder.service
  sudo sed -i '/^DeviceAllow=/d' /etc/systemd/system/recorder.service
  sudo sed -i '/^CapabilityBoundingSet=/d' /etc/systemd/system/recorder.service
  if ! grep -q '^PrivateDevices=no' /etc/systemd/system/recorder.service; then
    sudo sed -i '/^RestartSec=/a PrivateDevices=no' /etc/systemd/system/recorder.service
  fi
  sudo systemctl daemon-reload
  print_success "Systemd files patched"
}

enable_and_start_services() {
  print_status "Starting services..."
  for svc in booking_sync recorder video_worker system_status log_collector; do
    sudo systemctl enable "$svc"
    sudo systemctl restart "$svc"
    sleep 2
    if systemctl is-active --quiet "$svc"; then
      print_success "$svc started"
    else
      print_error "$svc failed to start"
      sudo journalctl -u "$svc" --no-pager | tail -n 10
    fi
  done
}

verify_camera() {
  print_status "Verifying camera..."
  if command -v libcamera-hello &>/dev/null; then
    if timeout 5 libcamera-hello --list-cameras &>/dev/null; then
      print_success "Camera detected"
    else
      print_warning "Camera not detected"
    fi
  fi
}

final_summary() {
  echo -e "\n🎉 ${GREEN}EZREC Backend (Core) deployed!${NC}"
  echo -e "${BLUE}[INFO]${NC} Legacy services started: recorder, booking_sync, etc."
  echo -e "${BLUE}[INFO]${NC} Your FastAPI + Cloudflare tunnel services are untouched."
  echo -e "${YELLOW}[NOTE]${NC} Reboot may be required for full camera activation."
}

main() {
  check_root
  cleanup_old_installation
  update_system
  install_packages
  setup_directories
  copy_project_files
  set_camera_permissions
  install_python_deps
  patch_systemd_services
  enable_and_start_services
  verify_camera
  final_summary
}

main "$@"
exit 0
