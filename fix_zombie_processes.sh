#!/bin/bash

echo "🧹 EZREC Zombie Process Cleanup"
echo "==============================="

echo "1️⃣ Identifying zombie rpicam-vid processes..."
echo "Current rpicam-vid processes:"
ps aux | grep rpicam-vid | grep -v grep

echo ""
echo "2️⃣ Killing all rpicam-vid processes..."
sudo pkill -f rpicam-vid
sleep 2

echo "3️⃣ Force killing any remaining processes..."
sudo pkill -9 -f rpicam-vid
sleep 1

echo "4️⃣ Clearing camera device locks..."
sudo fuser -k /dev/video* 2>/dev/null || true
sleep 1

echo "5️⃣ Resetting camera devices..."
sudo modprobe -r bcm2835_v4l2 2>/dev/null || true
sudo modprobe bcm2835_v4l2 2>/dev/null || true
sleep 2

echo "6️⃣ Verifying cleanup..."
remaining_processes=$(ps aux | grep rpicam-vid | grep -v grep | wc -l)
echo "Remaining rpicam-vid processes: $remaining_processes"

if [ $remaining_processes -eq 0 ]; then
    echo "✅ All zombie processes cleaned up successfully"
else
    echo "⚠️ Some processes may still be running:"
    ps aux | grep rpicam-vid | grep -v grep
fi

echo ""
echo "7️⃣ Testing camera availability..."
timeout 10 rpicam-vid --list-cameras 2>&1 | head -3

echo ""
echo "✅ Cleanup completed - ready for new recording test"
