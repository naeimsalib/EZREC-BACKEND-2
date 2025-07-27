#!/usr/bin/env python3
"""
Test suite for system_status.py
"""

import os
import sys
import tempfile
import json
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from system_status import SystemStatusMonitor

class TestSystemStatusMonitor(unittest.TestCase):
    """Test cases for SystemStatusMonitor"""
    
    def setUp(self):
        """Set up test environment"""
        self.monitor = SystemStatusMonitor()
        
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_ROLE_KEY': 'test-key',
            'USER_ID': 'test-user',
            'CAMERA_ID': 'test-camera',
            'TIMEZONE': 'UTC'
        })
        self.env_patcher.start()
    
    def tearDown(self):
        """Clean up after tests"""
        self.env_patcher.stop()
    
    @patch('psutil.disk_usage')
    def test_check_disk_space_healthy(self, mock_disk_usage):
        """Test disk space check with healthy usage"""
        # Mock disk usage (20% used)
        mock_disk_usage.return_value = MagicMock(
            percent=20.0,
            free=80 * (1024**3),  # 80 GB free
            total=100 * (1024**3)  # 100 GB total
        )
        
        result = self.monitor.check_disk_space()
        
        self.assertEqual(result['status'], 'healthy')
        self.assertEqual(result['usage_percent'], 20.0)
        self.assertEqual(result['free_gb'], 80.0)
        self.assertEqual(result['total_gb'], 100.0)
    
    @patch('psutil.disk_usage')
    def test_check_disk_space_critical(self, mock_disk_usage):
        """Test disk space check with critical usage"""
        # Mock disk usage (95% used)
        mock_disk_usage.return_value = MagicMock(
            percent=95.0,
            free=5 * (1024**3),  # 5 GB free
            total=100 * (1024**3)  # 100 GB total
        )
        
        result = self.monitor.check_disk_space()
        
        self.assertEqual(result['status'], 'critical')
        self.assertEqual(result['usage_percent'], 95.0)
    
    @patch('psutil.virtual_memory')
    def test_check_memory_usage(self, mock_memory):
        """Test memory usage check"""
        # Mock memory usage (50% used)
        mock_memory.return_value = MagicMock(
            percent=50.0,
            available=4 * (1024**3),  # 4 GB available
            total=8 * (1024**3)  # 8 GB total
        )
        
        result = self.monitor.check_memory_usage()
        
        self.assertEqual(result['status'], 'healthy')
        self.assertEqual(result['usage_percent'], 50.0)
        self.assertEqual(result['available_gb'], 4.0)
        self.assertEqual(result['total_gb'], 8.0)
    
    @patch('psutil.cpu_percent')
    def test_check_cpu_usage(self, mock_cpu):
        """Test CPU usage check"""
        # Mock CPU usage (30%)
        mock_cpu.return_value = 30.0
        
        result = self.monitor.check_cpu_usage()
        
        self.assertEqual(result['status'], 'healthy')
        self.assertEqual(result['usage_percent'], 30.0)
    
    @patch('subprocess.run')
    def test_check_services(self, mock_run):
        """Test service status check"""
        # Mock systemctl responses
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="active\n"),  # dual_recorder
            MagicMock(returncode=0, stdout="active\n"),  # video_worker
            MagicMock(returncode=1, stdout="inactive\n"),  # ezrec-api
            MagicMock(returncode=0, stdout="active\n"),  # system_status
        ]
        
        result = self.monitor.check_services()
        
        self.assertTrue(result['dual_recorder.service']['active'])
        self.assertTrue(result['video_worker.service']['active'])
        self.assertFalse(result['ezrec-api.service']['active'])
        self.assertTrue(result['system_status.service']['active'])
    
    @patch('subprocess.run')
    def test_check_ffmpeg_available(self, mock_run):
        """Test FFmpeg availability check"""
        # Mock successful FFmpeg version check
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ffmpeg version 4.2.7-0ubuntu0.1 Copyright (c) 2000-2022 the FFmpeg developers\n"
        )
        
        result = self.monitor.check_ffmpeg()
        
        self.assertEqual(result['status'], 'healthy')
        self.assertTrue(result['available'])
        self.assertIn('version', result)
    
    @patch('subprocess.run')
    def test_check_ffmpeg_not_available(self, mock_run):
        """Test FFmpeg not available"""
        # Mock failed FFmpeg check
        mock_run.return_value = MagicMock(returncode=1)
        
        result = self.monitor.check_ffmpeg()
        
        self.assertEqual(result['status'], 'error')
        self.assertFalse(result['available'])
    
    def test_extract_booking_id_from_filename(self):
        """Test booking ID extraction from filename"""
        from video_worker import extract_booking_id_from_filename
        
        test_cases = [
            ("143000_user123_cam456_merged.mp4", "user123_cam456"),
            ("143000_user123_cam456.done", "user123_cam456"),
            ("test_video.mp4", "test_video"),
            ("143000_merged.mp4", "143000_merged"),
            ("", ""),
        ]
        
        for filename, expected in test_cases:
            result = extract_booking_id_from_filename(filename)
            self.assertEqual(result, expected, f"Failed for {filename}")
    
    def test_generate_health_report(self):
        """Test health report generation"""
        with patch.object(self.monitor, 'check_disk_space') as mock_disk, \
             patch.object(self.monitor, 'check_memory_usage') as mock_memory, \
             patch.object(self.monitor, 'check_cpu_usage') as mock_cpu, \
             patch.object(self.monitor, 'check_services') as mock_services, \
             patch.object(self.monitor, 'check_camera_availability') as mock_camera, \
             patch.object(self.monitor, 'check_api_health') as mock_api, \
             patch.object(self.monitor, 'check_ffmpeg') as mock_ffmpeg, \
             patch.object(self.monitor, 'check_environment_variables') as mock_env, \
             patch.object(self.monitor, 'check_recording_status') as mock_recording, \
             patch.object(self.monitor, 'get_system_info') as mock_sysinfo:
            
            # Mock all health checks to return healthy status
            mock_disk.return_value = {'status': 'healthy', 'usage_percent': 20.0}
            mock_memory.return_value = {'status': 'healthy', 'usage_percent': 50.0}
            mock_cpu.return_value = {'status': 'healthy', 'usage_percent': 30.0}
            mock_services.return_value = {
                'dual_recorder.service': {'active': True},
                'video_worker.service': {'active': True},
                'ezrec-api.service': {'active': True},
                'system_status.service': {'active': True}
            }
            mock_camera.return_value = {'status': 'healthy', 'available': True, 'camera_count': 2}
            mock_api.return_value = {'status': 'healthy', 'responding': True}
            mock_ffmpeg.return_value = {'status': 'healthy', 'available': True}
            mock_env.return_value = {'status': 'healthy', 'all_set': True}
            mock_recording.return_value = {'status': 'idle', 'is_recording': False}
            mock_sysinfo.return_value = {'hostname': 'test-pi', 'uptime_hours': 24.5}
            
            report = self.monitor.generate_health_report()
            
            # Verify report structure
            self.assertIn('overall_status', report)
            self.assertIn('critical_issues', report)
            self.assertIn('warnings', report)
            self.assertEqual(report['overall_status'], 'healthy')
            self.assertEqual(len(report['critical_issues']), 0)
    
    def test_health_report_with_critical_issues(self):
        """Test health report with critical issues"""
        with patch.object(self.monitor, 'check_disk_space') as mock_disk, \
             patch.object(self.monitor, 'check_services') as mock_services, \
             patch.object(self.monitor, 'check_camera_availability') as mock_camera, \
             patch.object(self.monitor, 'check_api_health') as mock_api, \
             patch.object(self.monitor, 'check_ffmpeg') as mock_ffmpeg, \
             patch.object(self.monitor, 'check_environment_variables') as mock_env, \
             patch.object(self.monitor, 'check_recording_status') as mock_recording, \
             patch.object(self.monitor, 'get_system_info') as mock_sysinfo, \
             patch.object(self.monitor, 'check_memory_usage') as mock_memory, \
             patch.object(self.monitor, 'check_cpu_usage') as mock_cpu:
            
            # Mock critical disk usage
            mock_disk.return_value = {'status': 'critical', 'usage_percent': 95.0}
            mock_memory.return_value = {'status': 'healthy', 'usage_percent': 50.0}
            mock_cpu.return_value = {'status': 'healthy', 'usage_percent': 30.0}
            mock_services.return_value = {
                'dual_recorder.service': {'active': False},
                'video_worker.service': {'active': True},
                'ezrec-api.service': {'active': True},
                'system_status.service': {'active': True}
            }
            mock_camera.return_value = {'status': 'error', 'available': False}
            mock_api.return_value = {'status': 'error', 'responding': False}
            mock_ffmpeg.return_value = {'status': 'healthy', 'available': True}
            mock_env.return_value = {'status': 'healthy', 'all_set': True}
            mock_recording.return_value = {'status': 'idle', 'is_recording': False}
            mock_sysinfo.return_value = {'hostname': 'test-pi', 'uptime_hours': 24.5}
            
            report = self.monitor.generate_health_report()
            
            self.assertEqual(report['overall_status'], 'critical')
            self.assertGreater(len(report['critical_issues']), 0)
            self.assertIn('Disk space critical', report['critical_issues'])
            self.assertIn('Inactive services', report['critical_issues'])

def run_tests():
    """Run all tests"""
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSystemStatusMonitor)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 