from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
from pathlib import Path

app = FastAPI()

BOOKINGS_FILE = Path("/opt/ezrec-backend/api/local_data/bookings.json")
SYSTEM_FILE = Path("/opt/ezrec-backend/api/local_data/system.json")
RECORDINGS_DIR = Path("/opt/ezrec-backend/recordings")


# --------------------------
# MODELS
# --------------------------
class Booking(BaseModel):
    id: str
    user_id: str
    start_time: str
    end_time: str
    camera_id: str


class SystemSettings(BaseModel):
    main_logo_path: str
    sponsor_logo_paths: list[str]
    intro_video_path: str


# --------------------------
# ENDPOINTS
# --------------------------
@app.get("/")
def root():
    return {"message": "EZREC FastAPI is running"}


@app.get("/bookings")
def get_bookings():
    if BOOKINGS_FILE.exists():
        return json.loads(BOOKINGS_FILE.read_text())
    else:
        return []


@app.post("/bookings")
def post_bookings(bookings: list[Booking]):
    try:
        BOOKINGS_FILE.write_text(json.dumps([b.dict() for b in bookings], indent=2))
        return {"status": "success", "saved": len(bookings)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recordings")
def get_recordings():
    if not RECORDINGS_DIR.exists():
        return []

    recordings = []
    for date_dir in sorted(RECORDINGS_DIR.iterdir()):
        if not date_dir.is_dir():
            continue
        for f in date_dir.glob("*.mp4"):
            metadata_path = f.with_suffix(".json")
            if metadata_path.exists():
                metadata = json.loads(metadata_path.read_text())
                recordings.append(metadata)
            else:
                recordings.append({"filename": f.name, "path": str(f)})
    return recordings


@app.post("/system")
def update_system_settings(settings: SystemSettings):
    try:
        SYSTEM_FILE.write_text(json.dumps(settings.dict(), indent=2))
        return {"status": "success", "settings": settings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
