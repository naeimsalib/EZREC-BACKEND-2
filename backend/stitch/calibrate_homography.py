#!/usr/bin/env python3
"""
EZREC Homography Calibration Script
Computes homography matrix for panoramic video stitching
Run this once after camera setup or if cameras get bumped
"""

import cv2 as cv
import json
import numpy as np
import sys
from pathlib import Path
from stitch_config import get_config, get_logger

def compute_homography(img_left, img_right, min_matches=30):
    """Compute homography matrix between left and right images"""
    logger = get_logger()
    
    # ORB (free alternative to SIFT/SURF)
    orb = cv.ORB_create(nfeatures=get_config().get("orb_features", 4000))
    kpl, desl = orb.detectAndCompute(img_left, None)
    kpr, desr = orb.detectAndCompute(img_right, None)

    if desl is None or desr is None:
        raise RuntimeError("No descriptors found; ensure overlap and texture.")

    logger.info(f"Found {len(kpl)} keypoints in left image, {len(kpr)} in right image")

    # BFMatcher with Hamming for ORB
    bf = cv.BFMatcher(cv.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(desl, desr, k=2)

    # Lowe's ratio test
    good = []
    for m, n in matches:
        if m.distance < get_config().get("match_ratio", 0.75) * n.distance:
            good.append(m)

    if len(good) < min_matches:
        raise RuntimeError(f"Not enough good matches: {len(good)} < {min_matches}")

    logger.info(f"Found {len(good)} good matches out of {len(matches)} total")

    src = np.float32([kpl[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([kpr[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

    # Robust homography with RANSAC
    H, mask = cv.findHomography(
        dst, src, 
        method=cv.RANSAC, 
        ransacReprojThreshold=get_config().get("ransac_threshold", 3.0),
        maxIters=get_config().get("ransac_max_iter", 2000)
    )
    
    inliers = int(mask.sum()) if mask is not None else 0
    logger.info(f"Homography computed with {inliers} inliers out of {len(good)} matches")
    
    return H, inliers, len(good)

def validate_homography(H, img_left, img_right):
    """Validate homography matrix quality"""
    logger = get_logger()
    
    if H is None:
        logger.error("Homography matrix is None")
        return False
    
    # Check if matrix is reasonable
    if np.any(np.isnan(H)) or np.any(np.isinf(H)):
        logger.error("Homography matrix contains NaN or infinite values")
        return False
    
    # Check determinant (should be positive for proper transformation)
    det = np.linalg.det(H)
    if det <= 0:
        logger.warning(f"Homography determinant is {det:.6f} (should be positive)")
    
    # Test warping on corners
    h, w = img_right.shape[:2]
    corners = np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2)
    
    try:
        warped_corners = cv.perspectiveTransform(corners, H)
        logger.info("Homography validation passed - corner warping successful")
        return True
    except Exception as e:
        logger.error(f"Homography validation failed: {e}")
        return False

def main(left_frame_path, right_frame_path, out_json=None):
    """Main calibration function"""
    logger = get_logger()
    config = get_config()
    
    if out_json is None:
        out_json = config.get_homography_path()
    
    logger.info(f"Starting homography calibration...")
    logger.info(f"Left frame: {left_frame_path}")
    logger.info(f"Right frame: {right_frame_path}")
    logger.info(f"Output: {out_json}")
    
    # Read images
    img_left = cv.imread(left_frame_path)
    img_right = cv.imread(right_frame_path)
    
    if img_left is None or img_right is None:
        raise FileNotFoundError("Could not read input frames.")
    
    logger.info(f"Left image shape: {img_left.shape}")
    logger.info(f"Right image shape: {img_right.shape}")
    
    # Ensure images are in BGR format
    if len(img_left.shape) == 3:
        img_left = cv.cvtColor(img_left, cv.COLOR_BGR2GRAY)
    if len(img_right.shape) == 3:
        img_right = cv.cvtColor(img_right, cv.COLOR_BGR2GRAY)
    
    # Compute homography
    H, inliers, total = compute_homography(
        img_left, 
        img_right, 
        min_matches=config.get("min_matches", 30)
    )
    
    # Validate homography
    if not validate_homography(H, img_left, img_right):
        raise RuntimeError("Homography validation failed")
    
    # Prepare output data
    data = {
        "H": H.tolist(),
        "left_shape": img_left.shape[:2],
        "right_shape": img_right.shape[:2],
        "calibration_info": {
            "inliers": inliers,
            "total_matches": total,
            "match_ratio": inliers / total if total > 0 else 0,
            "timestamp": str(Path(left_frame_path).stat().st_mtime)
        },
        "config_used": {
            "orb_features": config.get("orb_features"),
            "min_matches": config.get("min_matches"),
            "match_ratio": config.get("match_ratio"),
            "ransac_threshold": config.get("ransac_threshold")
        }
    }
    
    # Ensure output directory exists
    out_path = Path(out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save homography data
    with open(out_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"✅ Homography calibration completed successfully!")
    logger.info(f"📁 Saved to: {out_path}")
    logger.info(f"📊 Quality: {inliers}/{total} matches ({inliers/total*100:.1f}% inliers)")
    
    return H, inliers, total

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Calibrate homography for EZREC panoramic stitching")
    parser.add_argument("left_frame", help="Left camera frame (JPG/PNG)")
    parser.add_argument("right_frame", help="Right camera frame (JPG/PNG)")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        H, inliers, total = main(args.left_frame, args.right_frame, args.output)
        print(f"✅ Calibration successful: {inliers}/{total} inliers")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Calibration failed: {e}")
        sys.exit(1) 