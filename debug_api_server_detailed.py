#!/usr/bin/env python3
"""
Detailed Debug API Server
Capture actual output to see why server exits
"""

import subprocess
import sys
import time

def main():
    print("🔍 DETAILED DEBUG API SERVER")
    print("="*50)
    
    print("🚀 Starting API server with output capture...")
    
    try:
        # Start API server and capture output in real-time
        process = subprocess.Popen([
            "/opt/ezrec-backend/api/venv/bin/python3",
            "/opt/ezrec-backend/api/api_server.py"
        ], 
        cwd="/opt/ezrec-backend/api",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
        )
        
        print(f"✅ Process started with PID: {process.pid}")
        print("📝 Capturing output (will timeout after 15 seconds)...")
        
        # Read output for up to 15 seconds
        start_time = time.time()
        output_lines = []
        
        while time.time() - start_time < 15:
            # Check if process is still running
            if process.poll() is not None:
                print(f"❌ Process exited with code: {process.returncode}")
                break
            
            # Try to read a line of output
            try:
                line = process.stdout.readline()
                if line:
                    line = line.strip()
                    output_lines.append(line)
                    print(f"📤 {line}")
                else:
                    time.sleep(0.1)
            except Exception as e:
                print(f"⚠️ Error reading output: {e}")
                break
        
        # Check final status
        if process.poll() is None:
            print("✅ Process is still running after 15 seconds")
            process.terminate()
            process.wait()
            print("✅ Process terminated")
        else:
            print(f"❌ Process exited with code: {process.returncode}")
        
        # Show all captured output
        print("\n📋 FULL OUTPUT CAPTURED:")
        print("="*50)
        for i, line in enumerate(output_lines, 1):
            print(f"{i:2d}: {line}")
        
        if not output_lines:
            print("No output captured - server may have exited immediately")
        
    except Exception as e:
        print(f"❌ Error starting API server: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 