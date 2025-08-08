#!/bin/bash
# Test script for seamless merge with 45-degree rotation
# Run this on your Raspberry Pi to validate the enhanced merge functionality

echo "🎬 Testing Seamless Merge with 45° Rotation"
echo "=============================================="

# Check if FFmpeg is available
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ FFmpeg not found. Please install FFmpeg first."
    exit 1
fi

echo "✅ FFmpeg found: $(ffmpeg -version | head -n1)"

# Create test directory
TEST_DIR="/tmp/ezrec_test_merge"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

echo "📁 Test directory: $TEST_DIR"

# Test 1: Quick validation command (as provided in the requirements)
echo ""
echo "📹 Test 1: Quick validation command with 45° rotation"
echo "----------------------------------------------------"

# Create a simple test video (if you have sample files, replace these paths)
LEFT_VIDEO="left.mp4"
RIGHT_VIDEO="right.mp4"

# Check if test files exist, if not create a note
if [ ! -f "$LEFT_VIDEO" ] || [ ! -f "$RIGHT_VIDEO" ]; then
    echo "⚠️  Test files not found. Please place left.mp4 and right.mp4 in $TEST_DIR"
    echo "   Or use your actual video files by updating the paths below."
    echo ""
    echo "📝 To test with your actual files, run:"
    echo "   LEFT_VIDEO=\"/path/to/your/left.mp4\""
    echo "   RIGHT_VIDEO=\"/path/to/your/right.mp4\""
    echo "   ./test_seamless_merge.sh"
    exit 1
fi

echo "✅ Test files found:"
echo "   Left:  $LEFT_VIDEO ($(du -h "$LEFT_VIDEO" | cut -f1))"
echo "   Right: $RIGHT_VIDEO ($(du -h "$RIGHT_VIDEO" | cut -f1))"

# Test the exact command from the requirements
echo ""
echo "🔧 Running FFmpeg command with 45° rotation and seamless blend..."

ffmpeg -y -i "$LEFT_VIDEO" -i "$RIGHT_VIDEO" \
-filter_complex "\
[0:v]rotate=PI/4:ow=rotw(PI/4):oh=roth(PI/4):c=black@0,scale=-2:1080,setsar=1[l]; \
[1:v]rotate=PI/4:ow=rotw(PI/4):oh=roth(PI/4):c=black@0,scale=-2:1080,setsar=1[r]; \
[l]crop=iw-100:ih:0:0[lm]; \
[l]crop=100:ih:iw-100:0[lo]; \
[r]crop=100:ih:0:0[ro]; \
[r]crop=iw-100:ih:100:0[rm]; \
[lo][ro]blend=all_expr='A*(1-X/W)+B*(X/W)'[b]; \
[lm][b][rm]hstack=inputs=3,format=yuv420p[v]" \
-map "[v]" -an -c:v libx264 -preset veryfast -crf 20 -movflags +faststart output_merged.mp4

if [ $? -eq 0 ]; then
    echo "✅ Test 1 successful! Output: output_merged.mp4 ($(du -h output_merged.mp4 | cut -f1))"
else
    echo "❌ Test 1 failed"
    exit 1
fi

# Test 2: Enhanced merge with Python script
echo ""
echo "📹 Test 2: Enhanced merge with Python script"
echo "--------------------------------------------"

# Check if Python script exists
if [ -f "/opt/ezrec-backend/backend/enhanced_merge.py" ]; then
    cd /opt/ezrec-backend
    echo "✅ Enhanced merge script found"
    
    # Test dry run
    echo "🔧 Testing dry run with 45° rotation..."
    python3 backend/enhanced_merge.py "$LEFT_VIDEO" "$RIGHT_VIDEO" output_enhanced.mp4 --method side_by_side --rotate 45 --dry-run
    
    # Test actual merge
    echo "🔧 Running actual merge with 45° rotation..."
    python3 backend/enhanced_merge.py "$LEFT_VIDEO" "$RIGHT_VIDEO" output_enhanced.mp4 --method side_by_side --rotate 45
    
    if [ $? -eq 0 ]; then
        echo "✅ Test 2 successful! Output: output_enhanced.mp4 ($(du -h output_enhanced.mp4 | cut -f1))"
    else
        echo "❌ Test 2 failed"
    fi
else
    echo "⚠️  Enhanced merge script not found at /opt/ezrec-backend/backend/enhanced_merge.py"
fi

# Test 3: Compare results
echo ""
echo "📹 Test 3: Comparing results"
echo "----------------------------"

if [ -f "output_merged.mp4" ] && [ -f "output_enhanced.mp4" ]; then
    echo "📊 File sizes:"
    echo "   Direct FFmpeg: $(du -h output_merged.mp4 | cut -f1)"
    echo "   Enhanced merge: $(du -h output_enhanced.mp4 | cut -f1)"
    
    # Get video info
    echo ""
    echo "📹 Video information:"
    echo "   Direct FFmpeg:"
    ffprobe -v quiet -print_format json -show_format -show_streams output_merged.mp4 | jq '.format.duration, .streams[0].width, .streams[0].height' 2>/dev/null || echo "   (ffprobe not available)"
    
    echo "   Enhanced merge:"
    ffprobe -v quiet -print_format json -show_format -show_streams output_enhanced.mp4 | jq '.format.duration, .streams[0].width, .streams[0].height' 2>/dev/null || echo "   (ffprobe not available)"
else
    echo "⚠️  Cannot compare - one or both output files missing"
fi

# Test 4: Test with different rotation angles
echo ""
echo "📹 Test 4: Testing different rotation angles"
echo "-------------------------------------------"

for angle in 0 45 90 135; do
    echo "🔧 Testing ${angle}° rotation..."
    python3 backend/enhanced_merge.py "$LEFT_VIDEO" "$RIGHT_VIDEO" "output_${angle}deg.mp4" --method side_by_side --rotate "$angle" --dry-run 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ ${angle}° rotation test successful"
    else
        echo "❌ ${angle}° rotation test failed"
    fi
done

echo ""
echo "🎬 Test Summary"
echo "==============="
echo "✅ All tests completed!"
echo "📁 Check output files in: $TEST_DIR"
echo ""
echo "📝 To test with your actual camera recordings:"
echo "   1. Copy your left and right camera MP4 files to $TEST_DIR"
echo "   2. Rename them to left.mp4 and right.mp4"
echo "   3. Run this script again"
echo ""
echo "🔧 To test the dual recorder with 45° rotation:"
echo "   1. Set CAMERA_ROTATION=0 in your .env file"
echo "   2. Set ENHANCED_MERGE_ROTATE_DEGREES=45.0 in your .env file"
echo "   3. Restart the dual recorder service"
