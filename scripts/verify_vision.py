"""Smoke-test real inference on official public MediaPipe test assets.

Downloads only the upstream test fixtures; never opens the user's webcam.
Raw fixture images stay in memory. The report contains counts/timing only.
"""
from pathlib import Path
from urllib.request import urlopen
import json
import os
import sys
import time
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'vision-py'))
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.local' / 'matplotlib'))
from src.detector import TrackerPool


def main():
    pool = TrackerPool(ROOT / 'vision-py/models')
    report = {}
    for layer, name, expected in [('face', 'portrait.jpg', 468), ('body', 'pose.jpg', 33), ('hand', 'pointing_up.jpg', 21)]:
        with urlopen('https://storage.googleapis.com/mediapipe-assets/' + name, timeout=30) as response:
            raw = response.read()
        decoded = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        h, w = decoded.shape[:2]
        ratio = min(1, 640 / max(w, h))
        decoded = cv2.resize(decoded, (int(w * ratio), int(h * ratio)))
        jpeg = cv2.imencode('.jpg', decoded, [cv2.IMWRITE_JPEG_QUALITY, 70])[1].tobytes()
        times = []
        for i in range(16):
            started = time.perf_counter()
            result = pool.extract('official-fixture-' + layer, layer, jpeg, (i + 1) * 67)
            times.append((time.perf_counter() - started) * 1000)
        assert len(result['landmarks']) == expected, (layer, result.get('message'))
        assert len(result['features']) == {'face': 52, 'body': 12, 'hand': 3}[layer]
        report[layer] = {'fixture': name, 'landmark_count': len(result['landmarks']),
                         'feature_count': len(result['features']), 'quality': result['quality'],
                         'gesture': result.get('gesture'), 'warm_inference_p50_ms': float(np.median(times[1:])),
                         'warm_inference_p95_ms': float(np.percentile(times[1:], 95)),
                         'measurement': 'Local CPU inference on a repeated public still image; not mobile end-to-end FPS.'}
        pool.release('official-fixture-' + layer)
    path = ROOT / 'docs' / 'vision-smoke.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
