#!/usr/bin/env python3
"""
EZREC Assets Setup Script
Creates placeholder assets for video processing
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv("/opt/ezrec-backend/.env")

def create_placeholder_image(output_path: Path, text: str, size: tuple = (200, 100)):
    """Create a placeholder image using ImageMagick or fallback"""
    try:
        # Try using ImageMagick
        import subprocess
        cmd = [
            'convert', '-size', f'{size[0]}x{size[1]}', 
            'xc:transparent', '-gravity', 'center',
            '-pointsize', '20', '-fill', 'white',
            '-annotate', '+0+0', text,
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ Created placeholder image: {output_path}")
        return True
    except Exception as e:
        print(f"⚠️ Could not create placeholder image: {e}")
        # Create a simple text file as fallback
        with open(output_path, 'w') as f:
            f.write(f"Placeholder for {text}\n")
        print(f"📝 Created placeholder file: {output_path}")
        return False

def create_placeholder_video(output_path: Path, duration: int = 3):
    """Create a placeholder video using FFmpeg"""
    try:
        import subprocess
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', f'color=c=black:size=1920x1080:duration={duration}',
            '-vf', 'drawtext=text=Intro:fontsize=60:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2',
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-t', str(duration),
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ Created placeholder video: {output_path}")
        return True
    except Exception as e:
        print(f"⚠️ Could not create placeholder video: {e}")
        # Create a simple text file as fallback
        with open(output_path, 'w') as f:
            f.write(f"Placeholder for intro video ({duration}s)\n")
        print(f"📝 Created placeholder file: {output_path}")
        return False

def main():
    """Main function to create assets"""
    print("🚀 EZREC Assets Setup")
    print("=====================")
    
    # Create assets directory
    assets_dir = Path("/opt/ezrec-backend/assets")
    assets_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Assets directory: {assets_dir}")
    
    # Create placeholder assets
    assets = [
        ("sponsor.png", "Sponsor Logo", (200, 100)),
        ("company.png", "Company Logo", (200, 100)),
        ("intro.mp4", "Intro Video", None)
    ]
    
    for filename, description, size in assets:
        asset_path = assets_dir / filename
        if not asset_path.exists():
            if filename.endswith('.mp4'):
                create_placeholder_video(asset_path)
            else:
                create_placeholder_image(asset_path, description, size)
        else:
            print(f"⏭️ Asset already exists: {filename}")
    
    print("\n✅ Assets setup completed!")
    print("📝 Note: These are placeholder assets. Replace with actual logos and intro video.")
    print("📁 Assets location: /opt/ezrec-backend/assets")

if __name__ == "__main__":
    main() 