#!/bin/bash

# EZREC Backend Full Cleanup Script
# This will remove all EZREC backend files, systemd units, venv, logs, and journald configs
# Use with caution! This is for a fresh start.

set -e

SERVICES=(recorder video_worker system_status log_collector health_api)
PROJECT_DIR="/opt/ezrec-backend"
VENV_DIR="$PROJECT_DIR/venv"
JOURNALD_CONF="/etc/systemd/journald.conf.d/ezrec.conf"

# 1. Stop and disable all services
for svc in "${SERVICES[@]}"; do
  sudo systemctl stop "$svc" 2>/dev/null || true
  sudo systemctl disable "$svc" 2>/dev/null || true
  sudo rm -f "/etc/systemd/system/${svc}.service"
done
sudo systemctl daemon-reload

echo "✅ All EZREC systemd services stopped, disabled, and removed."

# 2. Remove project directory
sudo rm -rf "$PROJECT_DIR"
echo "✅ Project directory $PROJECT_DIR removed."

# 3. Remove venv if present
sudo rm -rf "$VENV_DIR"
echo "✅ Python venv removed (if present)."

# 4. Remove journald config
sudo rm -f "$JOURNALD_CONF"
sudo systemctl restart systemd-journald
echo "✅ Journald config removed and journald restarted."

# 5. (Optional) Reboot
# echo "Rebooting in 5 seconds... Press Ctrl+C to cancel."
# sleep 5
# sudo reboot

echo "🎉 EZREC backend cleanup complete! You are ready for a fresh deployment." 