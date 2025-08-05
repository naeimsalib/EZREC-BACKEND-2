#!/usr/bin/env python3
"""
Simple test to run API server with same environment
"""

import subprocess
import sys
import os

def main():
    print("🔍 SIMPLE API SERVER TEST")
    print("="*40)
    
    # Test 1: Run with same environment as the API server
    print("🚀 Test 1: Running API server with same environment...")
    
    try:
        result = subprocess.run([
            "/opt/ezrec-backend/api/venv/bin/python3",
            "/opt/ezrec-backend/api/api_server.py"
        ], 
        cwd="/opt/ezrec-backend/api",
        capture_output=True,
        text=True,
        timeout=5,
        env=os.environ.copy()  # Use current environment
        )
        
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"Stdout:\n{result.stdout}")
        if result.stderr:
            print(f"Stderr:\n{result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("✅ Server is running (timeout reached)")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Try importing the API server module directly
    print("\n🚀 Test 2: Importing API server module...")
    
    try:
        # Add the API directory to Python path
        api_dir = "/opt/ezrec-backend/api"
        if api_dir not in sys.path:
            sys.path.insert(0, api_dir)
        
        # Try to import the module
        import api_server
        print("✅ Successfully imported api_server module")
        
        # Try to access the app
        if hasattr(api_server, 'app'):
            print("✅ API server app object exists")
        else:
            print("❌ API server app object not found")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Error importing module: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Check if we can run the main block
    print("\n🚀 Test 3: Testing main block execution...")
    
    try:
        # Create a simple test script
        test_script = """
import sys
import os
sys.path.insert(0, '/opt/ezrec-backend/api')

# Try to import and run main block
try:
    import api_server
    print("✅ Module imported successfully")
    
    # Check if __name__ == "__main__" would be true
    if __name__ == "__main__":
        print("✅ Would execute main block")
    else:
        print("ℹ️ Not in main block")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
"""
        
        result = subprocess.run([
            "/opt/ezrec-backend/api/venv/bin/python3", "-c", test_script
        ], 
        capture_output=True,
        text=True,
        timeout=10
        )
        
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"Output:\n{result.stdout}")
        if result.stderr:
            print(f"Error:\n{result.stderr}")
            
    except Exception as e:
        print(f"❌ Error running test script: {e}")

if __name__ == "__main__":
    main() 