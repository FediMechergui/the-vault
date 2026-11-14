"""MediaPipe Tasks in VIDEO mode. Each session owns its temporal trackers."""
from collections import OrderedDict
from pathlib import Path
import threading
import time
import cv2
import mediapipe as mp
import numpy as np
from vault_core.features import body_angles, face_geometry
from vault_core.signals import LandmarkFilter

MODEL_FILES = {"face": "face_landmarker.task", "body": "pose_landmarker_lite.task", "hand": "hand_landmarker.task"}


class Tracker:
    def __init__(self, layer, models):
        self.layer = layer
        self.lock = threading.Lock()
        self.touched = time.monotonic()
        self.last_timestamp = -1
        self.filter = LandmarkFilter()
        base = mp.tasks.BaseOptions(model_asset_path=str(models / MODEL_FILES[layer]))
        common = {"base_options": base, "running_mode": mp.tasks.vision.RunningMode.VIDEO}
        if layer == "face":
            options = mp.tasks.vision.FaceLandmarkerOptions(**common, num_faces=1, output_face_blendshapes=True)
            self.model = mp.tasks.vision.FaceLandmarker.create_from_options(options)
        elif layer == "body":
            options = mp.tasks.vision.PoseLandmarkerOptions(**common, num_poses=1)
            self.model = mp.tasks.vision.PoseLandmarker.create_from_options(options)
        else:
            options = mp.tasks.vision.HandLandmarkerOptions(**common, num_hands=1)
            self.model = mp.tasks.vision.HandLandmarker.create_from_options(options)

    def extract(self, jpeg, timestamp):
        with self.lock:
            self.touched = time.monotonic()
            if timestamp <= self.last_timestamp:
                raise ValueError("Timestamp must increase")
            self.last_timestamp = timestamp
            # Check dimensions before OpenCV allocation (JPEG decompression bomb guard).
            from PIL import Image
            import io
            with Image.open(io.BytesIO(jpeg)) as header:
                if header.format != "JPEG" or max(header.size) > 1280 or min(header.size) < 100:
                    raise ValueError("Expected a JPEG frame up to 1280 pixels")
            bgr = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
            if bgr is None:
                raise ValueError("Invalid JPEG")
            if float(np.mean(bgr)) < 22:
                return {"quality": False, "message": "Find a brighter spot", "landmarks": []}
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            result = self.model.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp)
            del bgr, rgb
            sets = getattr(result, {"face": "face_landmarks", "body": "pose_landmarks", "hand": "hand_landmarks"}[self.layer])
            if not sets:
                # Predict only for visual continuity; predictions never enter authentication.
                predicted = self.filter.update(None)
                return {"quality": False, "message": f"Bring your {self.layer} into frame",
                        "landmarks": predicted.tolist() if predicted is not None else []}
            points = np.array([[p.x, p.y, p.z] for p in sets[0]])
            if self.layer == "face":
                points = points[:468]  # Tasks returns 478: iris points are deliberately omitted.
            points = self.filter.update(points)
            payload = {"quality": True, "landmarks": points.tolist(), "message": "Tracking is clear"}
            if self.layer == "face":
                blends = result.face_blendshapes[0]
                named = {b.category_name: float(b.score) for b in blends}
                payload["features"] = [float(b.score) for b in sorted(blends, key=lambda b: b.index)]
                payload["geometry"] = face_geometry(points)
                payload["blink"] = min(named.get("eyeBlinkLeft", 0), named.get("eyeBlinkRight", 0))
                center = (points[234] + points[454]) / 2
                width = np.linalg.norm(points[234] - points[454])
                payload["yaw"] = float(-(points[1, 0] - center[0]) / max(width, 1e-5))
                payload["depth_ok"] = bool(np.ptp(points[:, 2]) > 0.015)
                if payload["blink"] > 0.55:
                    payload["gesture"] = "blink"
                elif max(named.get("mouthSmileLeft", 0), named.get("mouthSmileRight", 0)) > 0.55:
                    payload["gesture"] = "smile"
                elif max(named.get("eyeBlinkLeft", 0), named.get("eyeBlinkRight", 0)) > 0.55:
                    payload["gesture"] = "wink"
                else:
                    payload["gesture"] = "neutral"
            elif self.layer == "body":
                required = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 31, 32]
                visible = all(sets[0][i].visibility > 0.55 and 0.02 < points[i, 0] < 0.98
                              and 0.02 < points[i, 1] < 0.98 for i in required)
                payload["quality"] = visible
                payload["message"] = "Full body visible" if visible else "Step back; include both hands and feet"
                world = np.array([[p.x, p.y, p.z] for p in result.pose_world_landmarks[0]])
                payload["features"] = body_angles(world)
                up = [points[15, 1] < points[11, 1], points[16, 1] < points[12, 1]]
                payload["gesture"] = "arms raised" if all(up) else "one arm raised" if any(up) else "body tracked"
            else:
                palm = max(np.linalg.norm(points[0] - points[9]), 1e-5)
                payload["pinch"] = bool(np.linalg.norm(points[4] - points[8]) / palm < 0.28)
                payload["features"] = points[8].tolist()
                extended = sum(np.linalg.norm(points[tip] - points[0]) > np.linalg.norm(points[joint] - points[0]) * 1.1
                               for tip, joint in [(8, 6), (12, 10), (16, 14), (20, 18)])
                payload["gesture"] = "pinch" if payload["pinch"] else "open palm" if extended >= 4 else "pointing" if extended == 1 else "hand tracked"
                payload["message"] = "Pinch to start or finish" if payload["pinch"] else "Index fingertip tracked"
            return payload

    def close(self):
        with self.lock:
            self.model.close()


class TrackerPool:
    def __init__(self, models, capacity=5):
        self.models = Path(models)
        self.capacity = capacity
        self.items = OrderedDict()
        self.lock = threading.Lock()

    def extract(self, sid, layer, jpeg, timestamp):
        key = (sid, layer)
        with self.lock:
            now = time.monotonic()
            for old in [k for k, v in self.items.items() if now - v.touched > 60]:
                self.items.pop(old).close()
            if key not in self.items:
                if len(self.items) >= self.capacity:
                    self.items.popitem(last=False)[1].close()
                self.items[key] = Tracker(layer, self.models)
            tracker = self.items[key]
            self.items.move_to_end(key)
            # Retain pool lock until extraction completes; protects close/eviction.
            return tracker.extract(jpeg, timestamp)

    def release(self, sid):
        with self.lock:
            for key in [key for key in self.items if key[0] == sid]:
                self.items.pop(key).close()

    def ready(self):
        return all((self.models / name).is_file() for name in MODEL_FILES.values())
