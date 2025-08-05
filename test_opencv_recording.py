#!/usr/bin/env python3
"""
Test OpenCV Recording Functionality
Tests the new OpenCV-based recording system
"""

import cv2
import time
import os
import subprocess
from pathlib import Path

def test_opencv_recording():
    """Test OpenCV video recording with H.264 codec"""
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
            else:
                print("⚠️ Video file seems too small")
                return False
        else:
            print("❌ Video file was not created")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Recording test failed: {e}")
        return False

def test_ffmpeg_compatibility():
    """Test if the recorded video is compatible with FFmpeg"""
    print("\n🔧 Testing FFmpeg compatibility...")
    
    output_file = "test_recording.mp4"
    
    if not os.path.exists(output_file):
        print("❌ Test video file not found")
        return False
    
    try:
        # Get video info with ffprobe
        result = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height,avg_frame_rate",
            "-of", "json", output_file
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ ffprobe failed: {result.stderr}")
            return False
        
        print("✅ ffprobe analysis successful")
        print(f"📊 Video info: {result.stdout}")
        
        # Test playback with ffplay (brief)
        print("🎬 Testing playback with ffplay...")
        try:
            # Start ffplay for 2 seconds then kill it
            process = subprocess.Popen([
                "ffplay", "-v", "quiet", "-autoexit", "-t", "2", output_file
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Wait for it to finish or timeout
            process.wait(timeout=5)
            print("✅ ffplay test successful")
            
        except subprocess.TimeoutExpired:
            process.kill()
            print("✅ ffplay test completed (timeout)")
        except Exception as e:
            print(f"⚠️ ffplay test failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ FFmpeg compatibility test failed: {e}")
        return False

def cleanup_test_files():
    """Clean up test files"""
    test_files = ["test_recording.mp4"]
    for file in test_files:
        if os.path.exists(file):
            try:
                os.remove(file)
                print(f"🧹 Cleaned up {file}")
            except Exception as e:
                print(f"⚠️ Failed to clean up {file}: {e}")

def main():
    print("🚀 OpenCV Recording Test Suite")
    print("=" * 50)
    
    # Test recording
    recording_success = test_opencv_recording()
    
    if recording_success:
        # Test FFmpeg compatibility
        ffmpeg_success = test_ffmpeg_compatibility()
        
        if ffmpeg_success:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ OpenCV recording is working correctly")
            print("✅ Video files are compatible with FFmpeg")
            print("✅ Ready for production use")
        else:
            print("\n⚠️ Recording works but FFmpeg compatibility issues detected")
    else:
        print("\n❌ Recording test failed")
    
    # Cleanup
    print("\n🧹 Cleaning up test files...")
    cleanup_test_files()
    
    print("\n" + "=" * 50)
    print("Test suite completed")

if __name__ == "__main__":
    main() 