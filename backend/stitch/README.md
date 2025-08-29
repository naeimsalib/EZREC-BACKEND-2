# EZREC Panoramic Stitching System

OpenCV-based panoramic video stitching for dual-camera recordings.

## 🎯 Overview

This system provides true panoramic stitching using OpenCV's feature matching and homography transformation, replacing the basic side-by-side FFmpeg approach with professional-quality seamless blending.

## 📁 File Structure

```
stitch/
├── __init__.py                    # Package initialization
├── stitch_config.py               # Configuration and utilities
├── calibrate_homography.py        # Homography calibration script
├── stitch_videos.py               # Main video stitching script
├── calibrate_from_videos.py       # Frame extraction for calibration
├── test_stitching.py              # System testing script
├── requirements_stitch.txt         # OpenCV dependencies
├── README.md                      # This documentation
└── calibration/                   # Calibration files directory
    └── homography_right_to_left.json
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
# Navigate to backend directory
cd /opt/ezrec-backend/backend

# Activate virtual environment
source venv/bin/activate

# Install OpenCV dependencies
pip install -r stitch/requirements_stitch.txt
```

### 2. Calibration (One-time setup)
```bash
# Extract frames from existing videos
python3 stitch/calibrate_from_videos.py \
  /path/to/left_video.mp4 \
  /path/to/right_video.mp4

# Compute homography matrix
python3 stitch/calibrate_homography.py \
  calibration/left_frame.jpg \
  calibration/right_frame.jpg
```

### 3. Test Stitching
```bash
# Test with existing videos
python3 stitch/test_stitching.py --full-test \
  --left-video /path/to/left_video.mp4 \
  --right-video /path/to/right_video.mp4 \
  --output-video test_output.mp4
```

## 🔧 How It Works

### Phase 1: Calibration
1. **Frame Extraction**: Extract representative frames from both cameras
2. **Feature Detection**: Use ORB algorithm to find keypoints
3. **Feature Matching**: Match corresponding points between frames
4. **Homography Estimation**: Compute 3x3 transformation matrix using RANSAC
5. **Validation**: Verify matrix quality and save to JSON

### Phase 2: Production Stitching
1. **Load Homography**: Read pre-computed transformation matrix
2. **Frame Processing**: Process video frames in real-time
3. **Perspective Warp**: Apply homography to align right frame with left
4. **Seamless Blending**: Use feather masks or multi-band blending
5. **Output Generation**: Create panoramic video stream

## 📊 Performance Characteristics

- **Calibration**: One-time process (~30 seconds)
- **Stitching Speed**: 2-5x real-time on Raspberry Pi 5
- **Memory Usage**: ~200MB for 1080p processing
- **Output Quality**: Professional seamless panorama
- **File Size**: 20-60MB for 1-minute recording

## 🎛️ Configuration

### Key Parameters (stitch_config.py)
- `orb_features`: Number of ORB features (default: 4000)
- `min_matches`: Minimum good matches for homography (default: 30)
- `target_height`: Output video height (default: 1080)
- `overlap_pixels`: Overlap region width (default: 200)
- `use_multiband`: Enable multi-band blending (default: True)

### Environment Variables
- `OPENCV_STITCHING_ENABLED`: Enable/disable OpenCV stitching
- `STITCH_CALIBRATION_PATH`: Path to calibration files
- `STITCH_OUTPUT_QUALITY`: Output quality (1-10)

## 🔍 Troubleshooting

### Common Issues

#### 1. "No descriptors found"
- **Cause**: Insufficient overlap between camera views
- **Solution**: Ensure 15-30% overlap, add texture to scene

#### 2. "Not enough good matches"
- **Cause**: Poor feature matching
- **Solution**: Increase `orb_features`, improve lighting, add texture

#### 3. "Homography validation failed"
- **Cause**: Poor calibration quality
- **Solution**: Re-run calibration with better frames

#### 4. "Stitching too slow"
- **Cause**: High resolution processing
- **Solution**: Reduce `target_height`, enable downscaling

### Debug Commands
```bash
# Check OpenCV installation
python3 -c "import cv2; print(cv2.__version__)"

# Validate homography file
python3 -c "import json; data=json.load(open('calibration/homography_right_to_left.json')); print('Valid' if 'H' in data else 'Invalid')"

# Test stitching with verbose output
python3 stitch/test_stitching.py --full-test --left-video left.mp4 --right-video right.mp4 --verbose
```

## 🔄 Integration with EZREC

### Automatic Usage
The system automatically uses OpenCV stitching when:
1. OpenCV dependencies are installed
2. Homography file exists
3. `use_opencv_stitching=True` in configuration

### Fallback Behavior
If OpenCV stitching fails, the system automatically falls back to FFmpeg-based stitching.

### Service Integration
- **dual_recorder.py**: Records left/right videos
- **enhanced_merge.py**: Calls OpenCV stitching
- **video_worker.py**: Processes panoramic output

## 📈 Quality Improvements

### Before (FFmpeg)
- Side-by-side placement
- Visible seam between cameras
- No geometric correction
- Basic blending

### After (OpenCV)
- True panoramic alignment
- Seamless blending
- Geometric correction
- Professional output quality

## 🎥 Camera Setup Tips

### Optimal Configuration
1. **Overlap**: 15-30% between camera views
2. **Alignment**: Cameras should be parallel
3. **Height**: Same height for consistent perspective
4. **Lighting**: Even illumination across both views
5. **Texture**: Add visual features for better matching

### Calibration Best Practices
1. **Scene Selection**: Choose scenes with good texture
2. **Lighting**: Calibrate under similar lighting conditions
3. **Stability**: Ensure cameras don't move during calibration
4. **Validation**: Test stitching before production use

## 🔮 Future Enhancements

### Planned Features
- **Auto-calibration**: Automatic calibration from video streams
- **Dynamic Homography**: Adaptive transformation matrices
- **GPU Acceleration**: CUDA/OpenCL support for faster processing
- **Multi-camera Support**: Support for 3+ camera arrays
- **Real-time Streaming**: Live panoramic output

### Performance Optimizations
- **Frame Skipping**: Process every Nth frame for speed
- **Resolution Scaling**: Adaptive quality based on performance
- **Memory Management**: Optimized buffer handling
- **Parallel Processing**: Multi-threaded frame processing

## 📚 Technical References

- [OpenCV Homography Tutorial](https://docs.opencv.org/4.x/d7/dff/tutorial_feature_homography.html)
- [ORB Feature Detection](https://docs.opencv.org/4.x/d1/d89/tutorial_py_orb.html)
- [Multi-Band Blending](https://docs.opencv.org/4.x/d5/d4b/classcv_1_1detail_1_1MultiBandBlender.html)
- [Perspective Transform](https://docs.opencv.org/4.x/da/d54/group__imgproc__transform.html)

## 🤝 Support

For issues or questions:
1. Check troubleshooting section above
2. Review logs in `/opt/ezrec-backend/logs/`
3. Run test scripts to isolate problems
4. Verify OpenCV installation and dependencies

---

*This stitching system transforms basic dual-camera recordings into professional panoramic videos with seamless blending and geometric correction.* 