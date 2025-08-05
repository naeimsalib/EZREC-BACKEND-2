#!/usr/bin/env python3
"""
Diagnose API Server Issues
Investigates why API server starts but immediately exits
"""

import subprocess
import time
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return results"""
    print(f"\n🔍 {description}")
    print(f"Command: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"Output: {result.stdout.strip()}")
        if result.stderr:
            print(f"Error: {result.stderr.strip()}")
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        print("❌ Command timed out")
        return False, "", "Timeout"
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, "", str(e)

def check_api_server_file():
    """Check if API server file exists and is valid"""
    print("\n" + "="*60)
    print("📁 CHECKING API SERVER FILE")
    print("="*60)
    
    api_server_path = Path("/opt/ezrec-backend/api/api_server.py")
    
    if not api_server_path.exists():
        print(f"❌ API server file not found at {api_server_path}")
        return False
    
    print(f"✅ API server file found at {api_server_path}")
    
    # Check file size
    file_size = api_server_path.stat().st_size
    print(f"File size: {file_size} bytes")
    
    # Check if file is readable
    try:
        with open(api_server_path, 'r') as f:
            first_line = f.readline().strip()
            print(f"First line: {first_line}")
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False
    
    return True

def check_virtual_environment():
    """Check virtual environment"""
    print("\n" + "="*60)
    print("🐍 CHECKING VIRTUAL ENVIRONMENT")
    print("="*60)
    
    venv_path = Path("/opt/ezrec-backend/api/venv")
    
    if not venv_path.exists():
        print(f"❌ Virtual environment not found at {venv_path}")
        return False
    
    print(f"✅ Virtual environment found at {venv_path}")
    
    # Check Python executable
    python_path = venv_path / "bin" / "python3"
    if not python_path.exists():
        print(f"❌ Python executable not found at {python_path}")
        return False
    
    print(f"✅ Python executable found at {python_path}")
    
    # Test Python version
    success, output, error = run_command(
        f"{python_path} --version",
        "Check Python version"
    )
    
    if success:
        print(f"✅ Python version: {output}")
    else:
        print(f"❌ Failed to get Python version: {error}")
        return False
    
    return True

def check_dependencies():
    """Check if required dependencies are installed"""
    print("\n" + "="*60)
    print("📦 CHECKING DEPENDENCIES")
    print("="*60)
    
    # Check if requirements.txt exists
    requirements_path = Path("/opt/ezrec-backend/api/requirements.txt")
    if not requirements_path.exists():
        print(f"⚠️ Requirements file not found at {requirements_path}")
        # Check if it exists in the main directory
        main_requirements = Path("/opt/ezrec-backend/requirements.txt")
        if main_requirements.exists():
            print(f"✅ Requirements file found at {main_requirements}")
            requirements_path = main_requirements
        else:
            print("❌ No requirements.txt found")
            return False
    
    print(f"✅ Requirements file found at {requirements_path}")
    
    # Check if packages are installed
    python_path = "/opt/ezrec-backend/api/venv/bin/python3"
    
    # Test importing key packages
    packages_to_test = [
        "fastapi",
        "uvicorn", 
        "requests",
        "boto3",
        "psycopg2"
    ]
    
    for package in packages_to_test:
        success, output, error = run_command(
            f"{python_path} -c 'import {package}; print(f\"{package} version: {package.__version__}\")'",
            f"Test import {package}"
        )
        
        if success:
            print(f"✅ {package}: {output}")
        else:
            print(f"❌ {package}: {error}")
    
    return True

def test_api_server_syntax():
    """Test API server syntax"""
    print("\n" + "="*60)
    print("🔍 TESTING API SERVER SYNTAX")
    print("="*60)
    
    api_server_path = "/opt/ezrec-backend/api/api_server.py"
    python_path = "/opt/ezrec-backend/api/venv/bin/python3"
    
    success, output, error = run_command(
        f"{python_path} -m py_compile {api_server_path}",
        "Test API server syntax"
    )
    
    if success:
        print("✅ API server syntax is valid")
        return True
    else:
        print(f"❌ API server syntax error: {error}")
        return False

def test_api_server_import():
    """Test if API server can be imported"""
    print("\n" + "="*60)
    print("📥 TESTING API SERVER IMPORT")
    print("="*60)
    
    python_path = "/opt/ezrec-backend/api/venv/bin/python3"
    
    success, output, error = run_command(
        f"cd /opt/ezrec-backend/api && {python_path} -c 'import api_server; print(\"✅ API server imported successfully\")'",
        "Test API server import"
    )
    
    if success:
        print("✅ API server can be imported")
        return True
    else:
        print(f"❌ API server import failed: {error}")
        return False

def check_service_logs():
    """Check service logs for errors"""
    print("\n" + "="*60)
    print("📋 CHECKING SERVICE LOGS")
    print("="*60)
    
    success, output, error = run_command(
        "sudo journalctl -u api_server.service --no-pager -n 20",
        "Check recent API server service logs"
    )
    
    if success and output:
        print("✅ Service logs retrieved")
        print(f"Logs:\n{output}")
    else:
        print("❌ Could not retrieve service logs")
    
    # Check background process logs
    log_file = Path("/tmp/api_server.log")
    if log_file.exists():
        print(f"\n📄 Background process log file found at {log_file}")
        try:
            with open(log_file, 'r') as f:
                log_content = f.read()
                if log_content:
                    print(f"Log content:\n{log_content}")
                else:
                    print("Log file is empty")
        except Exception as e:
            print(f"❌ Error reading log file: {e}")
    else:
        print("❌ Background process log file not found")

def test_manual_start():
    """Test starting API server manually"""
    print("\n" + "="*60)
    print("🚀 TESTING MANUAL API SERVER START")
    print("="*60)
    
    python_path = "/opt/ezrec-backend/api/venv/bin/python3"
    api_server_path = "/opt/ezrec-backend/api/api_server.py"
    
    print("Starting API server manually (will timeout after 10 seconds)...")
    
    try:
        # Start API server with timeout
        result = subprocess.run(
            f"cd /opt/ezrec-backend/api && {python_path} {api_server_path}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")
            
        if result.returncode == 0:
            print("✅ API server started and exited normally")
        else:
            print(f"❌ API server exited with error code {result.returncode}")
            
    except subprocess.TimeoutExpired:
        print("✅ API server is running (timeout reached)")
        return True
    except Exception as e:
        print(f"❌ Error starting API server: {e}")
        return False

def check_port_conflicts():
    """Check for port conflicts"""
    print("\n" + "="*60)
    print("🔌 CHECKING PORT CONFLICTS")
    print("="*60)
    
    success, output, error = run_command(
        "sudo netstat -tlnp | grep :9000",
        "Check what's using port 9000"
    )
    
    if success and output:
        print(f"⚠️ Port 9000 is in use: {output}")
    else:
        print("✅ Port 9000 is not in use")
    
    # Check if any process is listening on port 9000
    success, output, error = run_command(
        "sudo lsof -i :9000",
        "Check processes using port 9000"
    )
    
    if success and output:
        print(f"Processes using port 9000: {output}")
    else:
        print("No processes using port 9000")

def main():
    """Main diagnostic function"""
    print("🔍 API SERVER DIAGNOSIS")
    print("="*60)
    print("Investigating why API server starts but immediately exits...")
    
    # Run all diagnostic checks
    checks = [
        ("File Check", check_api_server_file),
        ("Virtual Environment", check_virtual_environment),
        ("Dependencies", check_dependencies),
        ("Syntax Check", test_api_server_syntax),
        ("Import Test", test_api_server_import),
        ("Service Logs", check_service_logs),
        ("Port Conflicts", check_port_conflicts),
        ("Manual Start", test_manual_start),
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name} failed with error: {e}")
            results.append((check_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("📊 DIAGNOSIS SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{check_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All checks passed! API server should work.")
    elif passed >= total * 0.8:
        print("✅ Most checks passed. API server should work with minor issues.")
    else:
        print("⚠️ Several checks failed. API server has issues that need fixing.")

if __name__ == "__main__":
    main() 