#!/usr/bin/env python3
"""
Test basic imports for API server
"""

import sys
import os

def main():
    print("🔍 TESTING BASIC IMPORTS")
    print("="*40)
    
    print(f"Python version: {sys.version}")
    print(f"Python path: {sys.executable}")
    print(f"Working directory: {os.getcwd()}")
    
    # Test basic imports one by one
    imports_to_test = [
        ("supabase", "from supabase import create_client"),
        ("fastapi", "from fastapi import FastAPI"),
        ("pydantic", "from pydantic import BaseModel"),
        ("boto3", "import boto3"),
        ("dotenv", "from dotenv import load_dotenv"),
        ("uvicorn", "import uvicorn"),
        ("requests", "import requests"),
        ("numpy", "import numpy as np"),
        ("psutil", "import psutil"),
        ("pytz", "import pytz"),
    ]
    
    failed_imports = []
    
    for module_name, import_statement in imports_to_test:
        try:
            print(f"Testing {module_name}...", end=" ")
            exec(import_statement)
            print("✅ OK")
        except ImportError as e:
            print(f"❌ FAILED: {e}")
            failed_imports.append(module_name)
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed_imports.append(module_name)
    
    # Test environment variables
    print("\n🔍 TESTING ENVIRONMENT VARIABLES")
    print("="*40)
    
    env_vars = [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY", 
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_REGION",
        "AWS_S3_BUCKET"
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {'*' * min(len(value), 10)}...")
        else:
            print(f"❌ {var}: NOT SET")
    
    # Test .env file
    print("\n🔍 TESTING .env FILE")
    print("="*40)
    
    env_file = "/opt/ezrec-backend/.env"
    if os.path.exists(env_file):
        print(f"✅ .env file exists at {env_file}")
        try:
            with open(env_file, 'r') as f:
                lines = f.readlines()
            print(f"   Contains {len(lines)} lines")
        except Exception as e:
            print(f"❌ Error reading .env file: {e}")
    else:
        print(f"❌ .env file not found at {env_file}")
    
    # Test file permissions
    print("\n🔍 TESTING FILE PERMISSIONS")
    print("="*40)
    
    files_to_check = [
        "/opt/ezrec-backend/api/api_server.py",
        "/opt/ezrec-backend/.env",
        "/opt/ezrec-backend/api/local_data/",
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            try:
                if os.path.isfile(file_path):
                    with open(file_path, 'r') as f:
                        f.read(1)
                    print(f"✅ {file_path}: Readable")
                else:
                    os.listdir(file_path)
                    print(f"✅ {file_path}: Accessible directory")
            except Exception as e:
                print(f"❌ {file_path}: {e}")
        else:
            print(f"❌ {file_path}: Does not exist")
    
    # Summary
    print("\n📋 SUMMARY")
    print("="*40)
    
    if failed_imports:
        print(f"❌ Failed imports: {', '.join(failed_imports)}")
        print("   This could be the cause of the API server exit")
    else:
        print("✅ All imports successful")
    
    print(f"Python executable: {sys.executable}")
    print(f"Current working directory: {os.getcwd()}")

if __name__ == "__main__":
    main() 