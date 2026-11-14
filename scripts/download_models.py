"""Fetch official MediaPipe model assets; never download user images."""
from pathlib import Path
from urllib.request import urlretrieve
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://storage.googleapis.com/mediapipe-models"
MODELS = {
    "face_landmarker.task": f"{BASE}/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
    "pose_landmarker_lite.task": f"{BASE}/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
    "hand_landmarker.task": f"{BASE}/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
}


def download():
    target = ROOT / "vision-py" / "models"
    target.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, url in MODELS.items():
        path = target / name
        if not path.exists():
            temporary = path.with_suffix(".download")
            print(f"Downloading {name}", flush=True)
            urlretrieve(url, temporary)
            temporary.replace(path)
        manifest[name] = {"source": url, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    download()
