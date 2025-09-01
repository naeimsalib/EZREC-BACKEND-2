#!/bin/bash
echo "=== EZREC TEST LOGS - $(date) ===" > ezrec_test_logs_$(date +%Y%m%d_%H%M%S).txt

echo "--- SYSTEM STATUS ---" >> ezrec_test_logs_$(date +%Y%m%d_%H%M%S).txt
systemctl status dual_recorder.service video_worker.service ezrec-api.service system_status.service >> ezrec_test_logs_$(date +%Y%m%d_%H%M%S).txt 2>&1

echo "" >> ezrec_test_logs_$(date +%Y%m%d_%H%M%S).txt
echo "--- RECENT LOGS ---" >> ezrec_test_logs_$(date +%Y%m%d_%H%M%S).txt
journalctl -u dual_recorder.service --no-pager -n 50 >> ezrec_test_logs_$(date +%Y%m%d_%H%M%S).txt
echo "" >> ezrec_test_logs_$(date +%Y%m%d_%H%M%S).txt
journalctl -u video_worker.service --no-pager -n 50 >> ezrec_test_logs_$(date +%Y%m%d_%H%M%S).txt
echo "" >> ezrec_test_logs_$(date +%Y%m%d_%H%M%S).txt
journalctl -u ezrec-api.service --no-pager -n 50 >> ezrec_test_logs_$(date +%Y%m%d_%H%M%S).txt

echo "" >> ezrec_test_logs_$(date +%Y%m%d_%H%M%S).txt
echo "--- SYSTEM RESOURCES ---" >> ezrec_test_logs_$(date +%Y%m%d_%H%M%S).txt
df -h >> ezrec_test_logs_$(date +%Y%m%d_%H%M%S).txt
free -h >> ezrec_test_logs_$(date +%Y%m%d_%H%M%S).txt

echo "" >> ezrec_test_logs_$(date +%Y%m%d_%H%M%S).txt
echo "--- RECORDINGS CHECK ---" >> ezrec_test_logs_$(date +%Y%m%d_%H%M%S).txt
find /opt/ezrec-backend -name "*.mp4" -o -name "*.avi" -o -name "*.mov" >> ezrec_test_logs_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null

echo "" >> ezrec_test_logs_$(date +%Y%m%d_%H%M%S).txt
echo "--- STATUS FILE ---" >> ezrec_test_logs_$(date +%Y%m%d_%H%M%S).txt
cat /opt/ezrec-backend/status.json >> ezrec_test_logs_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null

echo "Logs saved to ezrec_test_logs_$(date +%Y%m%d_%H%M%S).txt"
