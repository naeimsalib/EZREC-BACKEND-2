#!/usr/bin/env python3
"""
FIX RECORDER ENCODING ISSUE
Updates the recorder to use software encoding instead of hardware encoding
"""

import subprocess
import os
import sys
from pathlib import Path

def run_command(cmd, check=True, capture_output=True, text=True):
    """Run a command and return result"""
    print(f"🔄 Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=capture_output, text=text)
        if result.stdout:
            print(f"✅ Output: {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e.stderr}")
        return e

def main():
    print("🔧 FIXING RECORDER ENCODING ISSUE")
    print("=" * 50)
    
    # Step 1: Stop the recorder service
    print("\n🛑 STEP 1: Stopping recorder service...")
    run_command("sudo systemctl stop recorder.service")
    
    # Step 2: Backup the original file
    print("\n💾 STEP 2: Backing up original recorder.py...")
    recorder_path = Path("/opt/ezrec-backend/backend/recorder.py")
    backup_path = recorder_path.with_suffix(".py.backup")
    
    if recorder_path.exists():
        run_command(f"cp {recorder_path} {backup_path}")
        print(f"✅ Backup created: {backup_path}")
    
    # Step 3: Update the recorder.py file
    print("\n📝 STEP 3: Updating recorder.py with software encoding...")
    
    # Read the current file
    with open(recorder_path, 'r') as f:
        content = f.read()
    
    # Replace hardware encoding with software encoding
    old_codec = "fourcc = cv2.VideoWriter_fourcc(*'avc1')  # H.264 codec"
    new_codec = "fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Software MP4 codec"
    
    if old_codec in content:
        content = content.replace(old_codec, new_codec)
        print("✅ Updated video codec from 'avc1' to 'mp4v'")
    else:
        print("⚠️ Could not find the codec line to replace")
    
    # Add fallback encoding options
    fallback_codecs = '''
            # Try multiple codecs in order of preference
            codecs_to_try = [
                ('mp4v', 'Software MP4'),
                ('XVID', 'XVID'),
                ('MJPG', 'Motion JPEG'),
                ('avc1', 'H.264 (hardware)')
            ]
            
            self.video_writer = None
            for codec_name, codec_desc in codecs_to_try:
                try:
                    fourcc = cv2.VideoWriter_fourcc(*codec_name)
                    self.video_writer = cv2.VideoWriter(
                        str(self.final_filepath),
                        fourcc,
                        RECORDING_FPS,
                        (width, height)
                    )
                    if self.video_writer.isOpened():
                        logger.info(f"✅ Using {codec_desc} codec: {codec_name}")
                        break
                    else:
                        self.video_writer.release()
                        logger.warning(f"⚠️ Failed to initialize {codec_desc} codec")
                except Exception as e:
                    logger.warning(f"⚠️ Error with {codec_desc} codec: {e}")
                    continue
'''
    
    # Replace the simple video writer initialization with the fallback version
    old_writer_init = '''            # Initialize video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Software MP4 codec
            self.video_writer = cv2.VideoWriter(
                str(self.final_filepath),
                fourcc,
                RECORDING_FPS,
                (width, height)
            )'''
    
    if old_writer_init in content:
        content = content.replace(old_writer_init, fallback_codecs)
        print("✅ Added fallback codec support")
    else:
        print("⚠️ Could not find video writer initialization to replace")
    
    # Write the updated content
    with open(recorder_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated recorder.py with software encoding support")
    
    # Step 4: Restart the recorder service
    print("\n🚀 STEP 4: Restarting recorder service...")
    run_command("sudo systemctl restart recorder.service")
    
    # Step 5: Check service status
    print("\n📋 STEP 5: Checking service status...")
    run_command("sudo systemctl status recorder.service", check=False)
    
    print("\n✅ RECORDER ENCODING FIX COMPLETE!")
    print("=" * 50)
    print("🔧 Changes made:")
    print("   - Changed from hardware 'avc1' to software 'mp4v' codec")
    print("   - Added fallback codec support (mp4v, XVID, MJPG, avc1)")
    print("   - Restarted recorder service")
    print("\n📋 Monitor the service with:")
    print("   sudo journalctl -u recorder.service -f")

if __name__ == "__main__":
    main() 