#!/usr/bin/env python3
"""
Test OpenCV Recording Functionality
Tests the new OpenCV-based recording system with fallback codecs
"""

import cv2
import time
import os
import subprocess
from pathlib import Path

def test_opencv_recording():
    """Test OpenCV video recording with fallback codecs"""
    print("🧪 Testing OpenCV Video Recording...")
    
    # Test parameters
    width, height = 1280, 720
    fps = 30
    duration = 5  # 5 seconds test recording
    output_file = "test_recording.mp4"
    
    try:
        # Initialize camera
        print("📹 Opening camera with OpenCV...")
        camera = cv2.VideoCapture(0)
        
        if not camera.isOpened():
            print("❌ Failed to open camera with OpenCV")
            return False
        
        # Configure camera settings
        print("⚙️ Configuring camera settings...")
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        camera.set(cv2.CAP_PROP_FPS, fps)
        
        # Get actual settings
        actual_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = camera.get(cv2.CAP_PROP_FPS)
        
        print(f"✅ Camera configured: {actual_width}x{actual_height} @ {actual_fps:.1f}fps")
        
        # Initialize video writer with fallback codecs
        print("🎬 Initializing video writer...")
        codecs_to_try = [
            ('mp4v', 'Software MP4'),
            ('XVID', 'XVID'),
            ('MJPG', 'Motion JPEG'),
            ('avc1', 'H.264 (hardware)')
        ]
        
        video_writer = None
        for codec_name, codec_desc in codecs_to_try:
            try:
                fourcc = cv2.VideoWriter_fourcc(*codec_name)
                video_writer = cv2.VideoWriter(
                    output_file,
                    fourcc,
                    fps,
                    (width, height)
                )
                if video_writer.isOpened():
                    print(f"✅ Using {codec_desc} codec: {codec_name}")
                    break
                else:
                    video_writer.release()
                    print(f"⚠️ Failed to initialize {codec_desc} codec")
            except Exception as e:
                print(f"⚠️ Error with {codec_desc} codec: {e}")
                continue
        
        if not video_writer or not video_writer.isOpened():
            print("❌ Failed to initialize video writer with any codec")
            return False
        
        print("✅ Video writer initialized successfully")
        
        # Record frames
        print(f"📹 Recording {duration} seconds of video...")
        frame_count = 0
        start_time = time.time()
        
        while time.time() - start_time < duration:
            ret, frame = camera.read()
            if not ret:
                print("⚠️ Failed to read frame from camera")
                continue
            
            # Resize frame if needed
            if frame.shape[1] != width or frame.shape[0] != height:
                frame = cv2.resize(frame, (width, height))
            
            # Write frame
            video_writer.write(frame)
            frame_count += 1
            
            # Show progress
            if frame_count % fps == 0:
                elapsed = time.time() - start_time
                print(f"📹 Recorded {frame_count} frames ({elapsed:.1f}s)")
        
        # Cleanup
        video_writer.release()
        camera.release()
        
        print(f"✅ Recording completed: {frame_count} frames")
        
        # Check if file was created and has content
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✅ Video file created: {output_file} ({file_size} bytes)")
            
            if file_size > 1024:  # At least 1KB
                print("✅ Video file has reasonable size")
                # Clean up test file
                os.remove(output_file)
                return True
            else:
                print("⚠️ Video file seems too small")
                return False
        else:
            print("❌ Video file was not created")
            return False
            
    except Exception as e:
        print(f"❌ Recording test failed: {e}")
        return False

def test_ffmpeg_compatibility():
    """Test if FFmpeg is available and working"""
    print("\n🔧 Testing FFmpeg compatibility...")
    
    try:
        # Test FFmpeg version
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ FFmpeg is available")
            # Extract version info
            version_line = result.stdout.split('\n')[0]
            print(f"📋 {version_line}")
            return True
        else:
            print("❌ FFmpeg command failed")
            return False
    except FileNotFoundError:
        print("❌ FFmpeg not found in PATH")
        return False
    except subprocess.TimeoutExpired:
        print("❌ FFmpeg command timed out")
        return False
    except Exception as e:
        print(f"❌ FFmpeg test failed: {e}")
        return False

def cleanup_test_files():
    """Clean up any test files"""
    test_files = ["test_recording.mp4", "test_output.mp4"]
    for file in test_files:
        if os.path.exists(file):
            try:
                os.remove(file)
                print(f"🧹 Cleaned up {file}")
            except Exception as e:
                print(f"⚠️ Could not remove {file}: {e}")

def main():
    """Main test function"""
    print("🚀 OpenCV Recording Test Suite")
    print("="*50)
    
    # Clean up any existing test files
    cleanup_test_files()
    
    # Test FFmpeg compatibility
    ffmpeg_ok = test_ffmpeg_compatibility()
    
    # Test OpenCV recording
    recording_ok = test_opencv_recording()
    
    # Summary
    print("\n" + "="*50)
    print("📊 TEST SUMMARY:")
    print(f"FFmpeg Compatibility: {'✅ PASS' if ffmpeg_ok else '❌ FAIL'}")
    print(f"OpenCV Recording: {'✅ PASS' if recording_ok else '❌ FAIL'}")
    
    if recording_ok and ffmpeg_ok:
        print("\n🎉 All tests passed! OpenCV recording is working correctly.")
        return True
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 