"""
EZREC Panoramic Stitching Package
OpenCV-based video stitching for dual-camera recordings
"""

from .stitch_config import get_config, get_logger
from .calibrate_homography import compute_homography
from .stitch_videos import PanoramicStitcher

__version__ = "1.0.0"
__all__ = [
    "get_config",
    "get_logger", 
    "compute_homography",
    "PanoramicStitcher"
] 