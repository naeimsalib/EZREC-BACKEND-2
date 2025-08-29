#!/usr/bin/env python3
"""
EZREC Panoramic Video Stitching Script
Fast video merging using pre-computed homography matrix
Optimized for Raspberry Pi 5 performance
"""

import cv2 as cv
import json
import numpy as np
import sys
import time
from pathlib import Path
from stitch_config import get_config, get_logger

class PanoramicStitcher:
    """OpenCV-based panoramic video stitcher"""
    
    def __init__(self, homography_path: str):
        self.logger = get_logger()
        self.config = get_config()
        self.H = self._load_homography(homography_path)
        self.logger.info("PanoramicStitcher initialized successfully")
    
    def _load_homography(self, json_path: str) -> np.ndarray:
        """Load homography matrix from JSON file"""
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            H = np.array(data["H"], dtype=np.float32)
            self.logger.info(f"Loaded homography matrix: {H.shape}")
            return H
            
        except Exception as e:
            raise RuntimeError(f"Failed to load homography: {e}")
    
    def _make_feather_masks(self, w: int, h: int, overlap_px: int = None):
        """Create feather masks for seamless blending"""
        if overlap_px is None:
            overlap_px = self.config.get("feather_overlap", 160)
        
        # Left image is full, right image fades in across overlap
        mask_left = np.ones((h, w), np.float32)
        mask_right = np.zeros((h, w), np.float32)
        
        # Create smooth fade-in ramp
        if overlap_px > 0:
            fade_ramp = np.linspace(0, 1, overlap_px, dtype=np.float32)
            mask_right[:, w-overlap_px:w] = fade_ramp
            
            # Smooth edges to avoid hard seams
            mask_left = np.clip(1.0 - mask_right, 0, 1)
        
        return mask_left, mask_right
    
    def _create_video_writer(self, out_path: str, width: int, height: int, fps: float):
        """Create video writer with appropriate codec"""
        try:
            # Try MP4V first (more compatible)
            fourcc = cv.VideoWriter_fourcc(*"mp4v")
            writer = cv.VideoWriter(out_path, fourcc, fps, (width, height))
            
            if not writer.isOpened():
                # Fallback to H264
                fourcc = cv.VideoWriter_fourcc(*"H264")
                writer = cv.VideoWriter(out_path, fourcc, fps, (width, height))
                
                if not writer.isOpened():
                    # Final fallback to MJPG
                    fourcc = cv.VideoWriter_fourcc(*"MJPG")
                    writer = cv.VideoWriter(out_path, fourcc, fps, (width, height))
            
            if not writer.isOpened():
                raise RuntimeError("Could not create video writer with any codec")
            
            self.logger.info(f"Video writer created: {width}x{height} @ {fps}fps")
            return writer
            
        except Exception as e:
            raise RuntimeError(f"Failed to create video writer: {e}")
    
    def _prepare_multiband_blender(self, width: int, height: int):
        """Prepare multi-band blender for seamless blending"""
        try:
            if not self.config.get("use_multiband", True):
                return None
            
            # Try to import opencv-contrib
            try:
                blender = cv.detail_MultiBandBlender()
                blender.prepare((0, 0, width, height))
                self.logger.info("Multi-band blender initialized")
                return blender
            except AttributeError:
                self.logger.warning("Multi-band blender not available, using feather blending")
                return None
                
        except Exception as e:
            self.logger.warning(f"Multi-band blender failed: {e}")
            return None
    
    def stitch_streams(self, left_path: str, right_path: str, out_path: str):
        """Main stitching function"""
        self.logger.info(f"Starting panoramic stitching...")
        self.logger.info(f"Left video: {left_path}")
        self.logger.info(f"Right video: {right_path}")
        self.logger.info(f"Output: {out_path}")
        
        start_time = time.time()
        
        # Open video captures
        capL = cv.VideoCapture(left_path)
        capR = cv.VideoCapture(right_path)
        
        if not (capL.isOpened() and capR.isOpened()):
            raise RuntimeError("Could not open input videos")
        
        # Get video properties
        fps = capL.get(cv.CAP_PROP_FPS) or self.config.get("fps", 30.0)
        total_frames = min(
            int(capL.get(cv.CAP_PROP_FRAME_COUNT)),
            int(capR.get(cv.CAP_PROP_FRAME_COUNT))
        )
        
        self.logger.info(f"Video properties: {fps}fps, ~{total_frames} frames")
        
        # Read first frames to determine dimensions
        retL, frameL = capL.read()
        retR, frameR = capR.read()
        
        if not (retL and retR):
            raise RuntimeError("Could not read first frames")
        
        # Get original dimensions
        hL, wL = frameL.shape[:2]
        hR, wR = frameR.shape[:2]
        
        self.logger.info(f"Left frame: {wL}x{hL}")
        self.logger.info(f"Right frame: {wR}x{hR}")
        
        # Calculate target dimensions
        target_height = self.config.get("target_height", 1080)
        scale = target_height / float(hL)
        new_wL = int(wL * scale)
        new_h = target_height
        
        # Calculate panorama dimensions
        overlap_px = self.config.get("overlap_pixels", 200)
        padding_px = self.config.get("padding_pixels", 320)
        pano_w = new_wL + int(new_wL * 0.6) + padding_px
        pano_h = new_h
        
        self.logger.info(f"Panorama dimensions: {pano_w}x{pano_h}")
        self.logger.info(f"Scale factor: {scale:.3f}")
        
        # Prepare blending components
        blender = self._prepare_multiband_blender(pano_w, pano_h)
        maskL, maskR = self._make_feather_masks(pano_w, pano_h, overlap_px)
        
        # Convert masks to 3-channel
        maskL3 = cv.merge([maskL, maskL, maskL])
        maskR3 = cv.merge([maskR, maskR, maskR])
        
        # Create video writer
        out_writer = self._create_video_writer(out_path, pano_w, pano_h, fps)
        
        # Processing loop
        frame_count = 0
        processing_times = []
        
        try:
            while True:
                frame_start = time.time()
                
                if frameL is None or frameR is None:
                    break
                
                # Resize frames
                frameLr = cv.resize(frameL, (new_wL, new_h), interpolation=cv.INTER_AREA)
                frameRr = cv.resize(frameR, (int(frameR.shape[1]*scale), new_h), interpolation=cv.INTER_AREA)
                
                # Warp right frame onto left plane
                warp = cv.warpPerspective(frameRr, self.H, (pano_w, pano_h))
                
                # Create canvas with left frame
                canvas = np.zeros_like(warp)
                canvas[0:new_h, 0:new_wL] = frameLr
                
                # Blend frames
                if blender is not None:
                    # Multi-band blending
                    try:
                        blender.feed(canvas.astype(np.float32), (0,0), np.ones((pano_h,pano_w), np.float32))
                        blender.feed(warp.astype(np.float32), (0,0), np.ones((pano_h,pano_w), np.float32))
                        result, _ = blender.blend(None, None)
                        frame_out = np.clip(result, 0, 255).astype(np.uint8)
                    except Exception as e:
                        self.logger.warning(f"Multi-band blending failed: {e}, falling back to feather")
                        blender = None
                
                if blender is None:
                    # Feather blending
                    blended = (canvas.astype(np.float32) * maskL3 + 
                              warp.astype(np.float32) * maskR3)
                    frame_out = np.clip(blended, 0, 255).astype(np.uint8)
                
                # Write frame
                out_writer.write(frame_out)
                
                # Progress tracking
                frame_count += 1
                processing_time = time.time() - frame_start
                processing_times.append(processing_time)
                
                if frame_count % 30 == 0:  # Log every 30 frames
                    avg_time = np.mean(processing_times[-30:])
                    fps_actual = 1.0 / avg_time if avg_time > 0 else 0
                    self.logger.info(f"Processed {frame_count}/{total_frames} frames, "
                                   f"avg: {avg_time*1000:.1f}ms, fps: {fps_actual:.1f}")
                
                # Read next frames
                retL, frameL = capL.read()
                retR, frameR = capR.read()
                
        except KeyboardInterrupt:
            self.logger.info("Stitching interrupted by user")
        except Exception as e:
            self.logger.error(f"Stitching error at frame {frame_count}: {e}")
            raise
        finally:
            # Cleanup
            out_writer.release()
            capL.release()
            capR.release()
            
            total_time = time.time() - start_time
            avg_processing = np.mean(processing_times) if processing_times else 0
            
            self.logger.info(f"✅ Stitching completed!")
            self.logger.info(f"📊 Frames processed: {frame_count}")
            self.logger.info(f"⏱️ Total time: {total_time:.1f}s")
            self.logger.info(f"📹 Output: {out_path}")
            self.logger.info(f"🎬 Average processing: {avg_processing*1000:.1f}ms per frame")
            
            if frame_count > 0:
                self.logger.info(f"🚀 Effective FPS: {frame_count/total_time:.1f}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="EZREC Panoramic Video Stitching")
    parser.add_argument("left_video", help="Left camera video file")
    parser.add_argument("right_video", help="Right camera video file")
    parser.add_argument("output_video", help="Output panoramic video file")
    parser.add_argument("homography_json", help="Homography calibration file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger = get_logger()
    
    try:
        # Validate inputs
        for path in [args.left_video, args.right_video, args.homography_json]:
            if not Path(path).exists():
                raise FileNotFoundError(f"File not found: {path}")
        
        # Create stitcher
        stitcher = PanoramicStitcher(args.homography_json)
        
        # Perform stitching
        stitcher.stitch_streams(args.left_video, args.right_video, args.output_video)
        
        print(f"✅ Panoramic stitching completed successfully!")
        print(f"📁 Output: {args.output_video}")
        
    except Exception as e:
        logger.error(f"Stitching failed: {e}")
        print(f"❌ Stitching failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 