#!/usr/bin/env python3
"""
EZREC Stitching Configuration and Utilities
Configuration file for OpenCV-based panoramic video stitching
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Default stitching parameters
DEFAULT_STITCH_CONFIG = {
    # Feature detection
    "orb_features": 4000,
    "min_matches": 30,
    "match_ratio": 0.75,
    
    # Homography estimation
    "ransac_threshold": 3.0,
    "ransac_max_iter": 2000,
    
    # Video processing
    "target_height": 1080,
    "overlap_pixels": 200,
    "padding_pixels": 320,
    "fps": 30.0,
    
    # Blending
    "use_multiband": True,
    "feather_overlap": 160,
    
    # Performance
    "downscale_for_merge": True,
    "upscale_after_merge": True,
    "interpolation": "INTER_AREA"  # cv2.INTER_AREA
}

class StitchConfig:
    """Configuration manager for stitching operations"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = DEFAULT_STITCH_CONFIG.copy()
        self.config_path = config_path or "stitch_config.json"
        self._load_config()
        self._setup_logging()
    
    def _load_config(self):
        """Load configuration from file if it exists"""
        try:
            if os.path.exists(self.config_path):
                import json
                with open(self.config_path, 'r') as f:
                    file_config = json.load(f)
                    self.config.update(file_config)
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")
    
    def _setup_logging(self):
        """Setup logging for stitching operations"""
        # Use existing EZREC logging if available
        try:
            # Try to get existing logger
            self.logger = logging.getLogger('ezrec.stitch')
        except:
            # Fallback to basic logging
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            self.logger = logging.getLogger('ezrec.stitch')
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            import json
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
    
    def get_calibration_path(self) -> Path:
        """Get path for calibration files"""
        return Path("calibration")
    
    def get_homography_path(self) -> Path:
        """Get path for homography JSON file"""
        return self.get_calibration_path() / "homography_right_to_left.json"
    
    def validate_camera_setup(self, left_path: str, right_path: str) -> bool:
        """Validate that camera setup is ready for stitching"""
        try:
            left_path = Path(left_path)
            right_path = Path(right_path)
            
            if not left_path.exists():
                self.logger.error(f"Left camera path not found: {left_path}")
                return False
            
            if not right_path.exists():
                self.logger.error(f"Right camera path not found: {right_path}")
                return False
            
            # Check if homography file exists
            homography_path = self.get_homography_path()
            if not homography_path.exists():
                self.logger.warning(f"Homography file not found: {homography_path}")
                self.logger.info("Run calibration first: python3 calibrate_homography.py")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Camera setup validation failed: {e}")
            return False

# Global configuration instance
stitch_config = StitchConfig()

def get_config() -> StitchConfig:
    """Get global stitching configuration"""
    return stitch_config

def get_logger():
    """Get stitching logger"""
    return get_config().logger 