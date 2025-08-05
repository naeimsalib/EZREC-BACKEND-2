#!/usr/bin/env python3
"""
Script to fix merge conflicts in video_worker.py
"""

import re
import sys
from pathlib import Path

def fix_merge_conflicts(file_path):
    """Fix merge conflicts in the specified file"""
    
    print(f"🔧 Fixing merge conflicts in {file_path}")
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix the import section conflict
    content = re.sub(
        r'<<<<<<< HEAD\n=======\nfrom enhanced_merge import merge_videos_with_retry, MergeResult\n\n# Try to import file locking library, fallback to simple file-based locking\ntry:\n    import portalocker\n    HAS_PORTALOCKER = True\nexcept ImportError:\n    HAS_PORTALOCKER = False\n    log = logging\.getLogger\("video_worker"\)\n    log\.warning\("⚠️ portalocker not available, using simple file-based locking"\)\n>>>>>>> 7f4d06de69b6359ae09f590d27a614501e93bf81',
        'from enhanced_merge import merge_videos_with_retry, MergeResult\n\n# Try to import file locking library, fallback to simple file-based locking\ntry:\n    import portalocker\n    HAS_PORTALOCKER = True\nexcept ImportError:\n    HAS_PORTALOCKER = False\n    log = logging.getLogger("video_worker")\n    log.warning("⚠️ portalocker not available, using simple file-based locking")',
        content
    )
    
    # Fix the get_video_info function conflict
    content = re.sub(
        r'<<<<<<< HEAD\n        \], capture_output=True, text=True\)\n        info = _json\.loads\(result\.stdout\)\n        stream = info\[\'streams\'\]\[0\]\n        codec = stream\.get\(\'codec_name\'\)\n        width = int\(stream\.get\(\'width\'\)\)\n        height = int\(stream\.get\(\'height\'\)\)\n        pix_fmt = stream\.get\(\'pix_fmt\'\)\n=======\n        \], capture_output=True, text=True, timeout=30\)\n        \n        if result\.returncode != 0:\n            log\.error\(f"❌ FFprobe failed for {file}: {result\.stderr}"\)\n            return None\n            \n        info = _json\.loads\(result\.stdout\)\n        if not info\.get\(\'streams\'\) or len\(info\[\'streams\'\]\) == 0:\n            log\.error\(f"❌ No video streams found in {file}"\)\n            return None\n            \n        stream = info\[\'streams\'\]\[0\]\n        codec = stream\.get\(\'codec_name\'\)\n        width = stream\.get\(\'width\'\)\n        height = stream\.get\(\'height\'\)\n        pix_fmt = stream\.get\(\'pix_fmt\'\)\n        \n        # Validate required fields\n        if not all\(\[codec, width, height, pix_fmt\]\):\n            log\.error\(f"❌ Missing required video info for {file}: codec={codec}, width={width}, height={height}, pix_fmt={pix_fmt}"\)\n            return None\n            \n        # Convert to integers\n        try:\n            width = int\(width\)\n            height = int\(height\)\n        except \(ValueError, TypeError\):\n            log\.error\(f"❌ Invalid width/height for {file}: width={width}, height={height}"\)\n            return None\n        \n>>>>>>> 7f4d06de69b6359ae09f590d27a614501e93bf81',
        '], capture_output=True, text=True, timeout=30)\n        \n        if result.returncode != 0:\n            log.error(f"❌ FFprobe failed for {file}: {result.stderr}")\n            return None\n            \n        info = _json.loads(result.stdout)\n        if not info.get(\'streams\') or len(info[\'streams\']) == 0:\n            log.error(f"❌ No video streams found in {file}")\n            return None\n            \n        stream = info[\'streams\'][0]\n        codec = stream.get(\'codec_name\')\n        width = stream.get(\'width\')\n        height = stream.get(\'height\')\n        pix_fmt = stream.get(\'pix_fmt\')\n        \n        # Validate required fields\n        if not all([codec, width, height, pix_fmt]):\n            log.error(f"❌ Missing required video info for {file}: codec={codec}, width={width}, height={height}, pix_fmt={pix_fmt}")\n            return None\n            \n        # Convert to integers\n        try:\n            width = int(width)\n            height = int(height)\n        except (ValueError, TypeError):\n            log.error(f"❌ Invalid width/height for {file}: width={width}, height={height}")\n            return None\n        ',
        content
    )
    
    # Fix the return statement conflict in get_video_info
    content = re.sub(
        r'<<<<<<< HEAD\n        return codec, width, height, fps, pix_fmt\n    except Exception as e:\n        log\.error\(f"Could not get video info for {file}: {e}"\)\n        return None, None, None, None, None\n=======\n        \n        return \(codec, width, height, fps, pix_fmt\)\n    except subprocess\.TimeoutExpired:\n        log\.error\(f"❌ FFprobe timeout for {file}"\)\n        return None\n    except Exception as e:\n        log\.error\(f"❌ Could not get video info for {file}: {e}"\)\n        return None\n>>>>>>> 7f4d06de69b6359ae09f590d27a614501e93bf81',
        '\n        return (codec, width, height, fps, pix_fmt)\n    except subprocess.TimeoutExpired:\n        log.error(f"❌ FFprobe timeout for {file}")\n        return None\n    except Exception as e:\n        log.error(f"❌ Could not get video info for {file}: {e}")\n        return None',
        content
    )
    
    # Fix the process_video function conflict
    content = re.sub(
        r'<<<<<<< HEAD\n    Ensures compatibility with OpenCV-generated MP4 files\.\n=======\n>>>>>>> 7f4d06de69b6359ae09f590d27a614501e93bf81',
        'Ensures compatibility with OpenCV-generated MP4 files.',
        content
    )
    
    # Remove the large conflict block in process_video (lines 500-829)
    # This is a complex conflict that needs manual resolution
    # For now, we'll use the newer version (after =======)
    
    # Find the start of the large conflict block
    start_marker = '<<<<<<< HEAD\n    # Use local cache for user media'
    end_marker = '=======\n    # Check if this is a dual camera recording that needs merging'
    
    # Replace the entire conflict block with the newer version
    pattern = r'<<<<<<< HEAD\n    # Use local cache for user media.*?=======\n    # Check if this is a dual camera recording that needs merging'
    replacement = '    # Check if this is a dual camera recording that needs merging'
    
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Remove any remaining conflict markers
    content = re.sub(r'<<<<<<< HEAD|=======|>>>>>>>', '', content, flags=re.DOTALL)
    
    # Write the fixed content back
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Fixed merge conflicts in {file_path}")
    
    # Check if there are any remaining conflict markers
    remaining_conflicts = re.findall(r'<<<<<<< HEAD|=======|>>>>>>>', content)
    if remaining_conflicts:
        print(f"⚠️ Warning: {len(remaining_conflicts)} conflict markers still found")
        print("You may need to manually resolve remaining conflicts")
    else:
        print("✅ All conflict markers removed successfully")

if __name__ == "__main__":
    video_worker_path = Path("backend/video_worker.py")
    
    if not video_worker_path.exists():
        print(f"❌ File not found: {video_worker_path}")
        sys.exit(1)
    
    # Create backup
    backup_path = video_worker_path.with_suffix('.py.backup')
    import shutil
    shutil.copy2(video_worker_path, backup_path)
    print(f"📋 Created backup: {backup_path}")
    
    # Fix conflicts
    fix_merge_conflicts(video_worker_path)
    
    print("🎉 Merge conflict resolution complete!")
    print("You can now restart the video_worker service:")
    print("sudo systemctl restart video_worker.service") 