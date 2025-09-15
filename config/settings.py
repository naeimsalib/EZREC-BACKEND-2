#!/usr/bin/env python3
"""
EZREC Centralized Configuration Management
Single source of truth for all application settings
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path="/opt/ezrec-backend/.env")

@dataclass
class DatabaseConfig:
    """Database configuration"""
    supabase_url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    supabase_key: str = field(default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
    
    def validate(self) -> bool:
        """Validate database configuration"""
        return bool(self.supabase_url and self.supabase_key)

@dataclass
class StorageConfig:
    """Storage configuration"""
    aws_access_key: str = field(default_factory=lambda: os.getenv("AWS_ACCESS_KEY_ID", ""))
    aws_secret_key: str = field(default_factory=lambda: os.getenv("AWS_SECRET_ACCESS_KEY", ""))
    aws_region: str = field(default_factory=lambda: os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
    s3_bucket: str = field(default_factory=lambda: os.getenv("S3_BUCKET", ""))
    
    def validate(self) -> bool:
        """Validate storage configuration"""
        return bool(self.aws_access_key and self.aws_secret_key and self.s3_bucket)

@dataclass
class CameraConfig:
    """Camera configuration"""
    recording_width: int = 1280
    recording_height: int = 720
    recording_framerate: int = 30
    recording_timeout: int = 300000  # 5 minutes in milliseconds
    
    def validate(self) -> bool:
        """Validate camera configuration"""
        return all([
            self.recording_width > 0,
            self.recording_height > 0,
            self.recording_framerate > 0,
            self.recording_timeout > 0
        ])

@dataclass
class PathConfig:
    """Path configuration"""
    deploy_path: Path = field(default_factory=lambda: Path("/opt/ezrec-backend"))
    recordings_path: Path = field(default_factory=lambda: Path("/opt/ezrec-backend/recordings"))
    bookings_path: Path = field(default_factory=lambda: Path("/opt/ezrec-backend/api/local_data"))
    logs_path: Path = field(default_factory=lambda: Path("/opt/ezrec-backend/logs"))
    
    def __post_init__(self):
        """Ensure all paths exist"""
        for path in [self.recordings_path, self.bookings_path, self.logs_path]:
            path.mkdir(parents=True, exist_ok=True)

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get configured logger"""
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, self.level.upper(), logging.INFO))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(self.format)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger

@dataclass
class APIConfig:
    """API configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    
    def validate(self) -> bool:
        """Validate API configuration"""
        return 0 < self.port < 65536

class Settings:
    """Main settings class"""
    
    def __init__(self):
        self.database = DatabaseConfig()
        self.storage = StorageConfig()
        self.camera = CameraConfig()
        self.paths = PathConfig()
        self.logging = LoggingConfig()
        self.api = APIConfig()
        
        # Validate all configurations
        self._validate()
    
    def _validate(self):
        """Validate all configurations"""
        if not self.database.validate():
            raise ValueError("Invalid database configuration")
        
        if not self.storage.validate():
            raise ValueError("Invalid storage configuration")
        
        if not self.camera.validate():
            raise ValueError("Invalid camera configuration")
        
        if not self.api.validate():
            raise ValueError("Invalid API configuration")
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get configured logger"""
        return self.logging.get_logger(name)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary"""
        return {
            "database": {
                "supabase_url": self.database.supabase_url,
                "supabase_key": "***" if self.database.supabase_key else None
            },
            "storage": {
                "aws_region": self.storage.aws_region,
                "s3_bucket": self.storage.s3_bucket,
                "aws_access_key": "***" if self.storage.aws_access_key else None
            },
            "camera": {
                "recording_width": self.camera.recording_width,
                "recording_height": self.camera.recording_height,
                "recording_framerate": self.camera.recording_framerate,
                "recording_timeout": self.camera.recording_timeout
            },
            "paths": {
                "deploy_path": str(self.paths.deploy_path),
                "recordings_path": str(self.paths.recordings_path),
                "bookings_path": str(self.paths.bookings_path),
                "logs_path": str(self.paths.logs_path)
            },
            "api": {
                "host": self.api.host,
                "port": self.api.port,
                "debug": self.api.debug
            }
        }

# Global settings instance
settings = Settings()

# Convenience functions
def get_logger(name: str) -> logging.Logger:
    """Get configured logger"""
    return settings.get_logger(name)

def get_database_client():
    """Get Supabase client"""
    from supabase import create_client
    return create_client(settings.database.supabase_url, settings.database.supabase_key)

def get_s3_client():
    """Get S3 client"""
    import boto3
    return boto3.client(
        's3',
        aws_access_key_id=settings.storage.aws_access_key,
        aws_secret_access_key=settings.storage.aws_secret_key,
        region_name=settings.storage.aws_region
    )
