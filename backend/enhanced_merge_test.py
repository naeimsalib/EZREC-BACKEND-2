#!/usr/bin/env python3
"""
Unit tests for enhanced_merge.py
- Tests missing input file
- Tests corrupt video file
- Simulates FFmpeg failure
- Tests successful merge
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path
import pytest
from backend.enhanced_merge import merge_videos_with_retry, MergeResult

test_dir = Path("/tmp/enhanced_merge_test")
test_dir.mkdir(exist_ok=True)

def create_test_video(path: Path, color: str = 'red', duration: int = 2):
    """Create a simple test video using FFmpeg"""
    cmd = [
        'ffmpeg', '-y', '-f', 'lavfi', '-i', f"color=c={color}:s=320x240:d={duration}",
        '-c:v', 'libx264', '-t', str(duration), str(path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)

def test_missing_input():
    video1 = test_dir / "missing1.mp4"
    video2 = test_dir / "missing2.mp4"
    output = test_dir / "output_missing.mp4"
    result = merge_videos_with_retry(video1, video2, output)
    assert not result.success
    assert "not found" in (result.error_message or "")

def test_corrupt_input():
    video1 = test_dir / "corrupt1.mp4"
    video2 = test_dir / "corrupt2.mp4"
    output = test_dir / "output_corrupt.mp4"
    # Create a corrupt file
    with open(video1, 'wb') as f:
        f.write(b"not a video")
    create_test_video(video2, color='blue')
    result = merge_videos_with_retry(video1, video2, output)
    assert not result.success
    assert "validation" in (result.error_message or "") or "error" in (result.error_message or "")

def test_ffmpeg_failure(monkeypatch):
    video1 = test_dir / "ffmpeg1.mp4"
    video2 = test_dir / "ffmpeg2.mp4"
    output = test_dir / "output_ffmpeg.mp4"
    create_test_video(video1, color='yellow')
    create_test_video(video2, color='green')
    # Monkeypatch subprocess.run to simulate FFmpeg failure
    import backend.enhanced_merge as em
    orig_run = subprocess.run
    def fake_run(*args, **kwargs):
        if 'ffmpeg' in args[0]:
            return subprocess.CompletedProcess(args[0], 1, stdout='', stderr='Simulated FFmpeg error')
        return orig_run(*args, **kwargs)
    monkeypatch.setattr(em.subprocess, 'run', fake_run)
    result = em.merge_videos_with_retry(video1, video2, output)
    assert not result.success
    assert "FFmpeg failed" in (result.error_message or "")
    monkeypatch.setattr(em.subprocess, 'run', orig_run)

def test_successful_merge():
    video1 = test_dir / "success1.mp4"
    video2 = test_dir / "success2.mp4"
    output = test_dir / "output_success.mp4"
    create_test_video(video1, color='red')
    create_test_video(video2, color='blue')
    result = merge_videos_with_retry(video1, video2, output)
    assert result.success
    assert output.exists()
    assert result.file_size > 0
    output.unlink(missing_ok=True)
    video1.unlink(missing_ok=True)
    video2.unlink(missing_ok=True)

def teardown_module(module):
    shutil.rmtree(test_dir, ignore_errors=True)

if __name__ == "__main__":
    print("Running enhanced_merge.py unit tests...")
    test_missing_input()
    print("✅ test_missing_input passed")
    test_corrupt_input()
    print("✅ test_corrupt_input passed")
    # test_ffmpeg_failure requires pytest monkeypatch fixture
    test_successful_merge()
    print("✅ test_successful_merge passed")
    print("All basic tests passed. For FFmpeg failure test, run with pytest.") 