#!/usr/bin/env python3
import os
import time
import subprocess
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder

# ─── CONFIG ────────────────────────────────────────────────────────────────
DURATION   = 5               # seconds to record
RESOLUTION = (1920, 1080)    # width, height
FRAMERATE  = 30              # fps
BITRATE    = 6_000_000       # 6 Mbps
OUTPUT_DIR = "recordings"    # output folder
# ────────────────────────────────────────────────────────────────────────────

def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def record_dual():
    # 1) Initialize and configure both cameras
    cam0 = Picamera2(0)
    cam1 = Picamera2(1)

    cfg0 = cam0.create_video_configuration(
        main={"size": RESOLUTION, "format": "YUV420"},
        controls={"FrameDurationLimits": (int(1e6/FRAMERATE), int(1e6/FRAMERATE))}
    )
    cfg1 = cam1.create_video_configuration(
        main={"size": RESOLUTION, "format": "YUV420"},
        controls={"FrameDurationLimits": (int(1e6/FRAMERATE), int(1e6/FRAMERATE))}
    )

    cam0.configure(cfg0)
    cam1.configure(cfg1)

    encoder0 = H264Encoder(bitrate=BITRATE)
    encoder1 = H264Encoder(bitrate=BITRATE)

    out0 = os.path.join(OUTPUT_DIR, "cam0.h264")
    out1 = os.path.join(OUTPUT_DIR, "cam1.h264")

    print(f"[Cam0] ⏺️  Recording → {out0}")
    print(f"[Cam1] ⏺️  Recording → {out1}")

    # 2) Start both recordings simultaneously
    cam0.start_recording(encoder0, out0)
    cam1.start_recording(encoder1, out1)

    time.sleep(DURATION)

    # 3) Stop and close
    cam0.stop_recording()
    cam1.stop_recording()
    cam0.close()
    cam1.close()
    print("[Dual] ✅  Both recordings complete")

def package_mp4():
    print("[Package] Packaging .h264 → .mp4…")
    for cam in (0, 1):
        raw = os.path.join(OUTPUT_DIR, f"cam{cam}.h264")
        mp4 = os.path.join(OUTPUT_DIR, f"cam{cam}.mp4")
        subprocess.run([
            "ffmpeg", "-y",
            "-framerate", str(FRAMERATE),
            "-i", raw,
            "-c", "copy",
            mp4
        ], check=True)
        print(f"   ✂️  {raw} → {mp4}")

def merge_wide():
    in0 = os.path.join(OUTPUT_DIR, "cam0.mp4")
    in1 = os.path.join(OUTPUT_DIR, "cam1.mp4")
    out = os.path.join(OUTPUT_DIR, "merged_wide.mp4")
    print(f"[Merge] Merging side‑by‑side → {out}")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", in0,
        "-i", in1,
        "-filter_complex", "hstack=inputs=2",
        "-c:v", "libx264", "-preset", "fast",
        out
    ], check=True)
    print(f"[Merge] ✅  Merged to {out}")

if __name__ == "__main__":
    ensure_output_dir()
    record_dual()
    package_mp4()
    merge_wide()
    print(f"\n🎉 All done! Check your videos in: {OUTPUT_DIR}/merged_wide.mp4")