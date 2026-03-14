import time
from pathlib import Path
import requests

WATCH_DIR = Path("demo_frames")
API_URL = "http://localhost:8000/api/camera-frame"
SEEN = set()

WATCH_DIR.mkdir(exist_ok=True)

print(f"Watching {WATCH_DIR.resolve()} for new images...")

while True:
    for path in WATCH_DIR.glob("*"):
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            continue
        if path in SEEN:
            continue

        try:
            with open(path, "rb") as f:
                files = {"file": (path.name, f, "image/jpeg")}
                r = requests.post(API_URL, files=files, timeout=5)
                print(path.name, r.status_code, r.text)
            SEEN.add(path)
        except Exception as e:
            print(f"Failed for {path.name}: {e}")

    time.sleep(2)
