from __future__ import annotations

import numpy as np

# Twelve joint angles: elbows, shoulders, hips, knees, ankles and torso.
JOINTS = [(11, 13, 15), (12, 14, 16), (13, 11, 23), (14, 12, 24),
          (11, 23, 25), (12, 24, 26), (23, 25, 27), (24, 26, 28),
          (25, 27, 31), (26, 28, 32), (12, 11, 23), (11, 12, 24)]
FACE_ANCHORS = [10, 152, 234, 454, 33, 263, 133, 362, 1, 4, 61, 291, 168, 6, 197,
                50, 280, 172, 397, 93]
FACE_PAIRS = [(FACE_ANCHORS[i], FACE_ANCHORS[(i + offset) % len(FACE_ANCHORS)])
              for offset in (1, 3, 7) for i in range(len(FACE_ANCHORS))]


def face_geometry(points):
    p = np.asarray(points, dtype=float)
    if p.shape != (468, 3):
        raise ValueError("Expected 468 face landmarks")
    scale = np.linalg.norm(p[33] - p[263])
    if scale < 0.01:
        raise ValueError("Move closer to the camera")
    return [float(np.linalg.norm(p[a] - p[b]) / scale) for a, b in FACE_PAIRS]


def body_angles(points):
    p = np.asarray(points, dtype=float)
    center = (p[23] + p[24]) / 2
    scale = np.linalg.norm((p[11] + p[12]) / 2 - center)
    if scale < 1e-4:
        raise ValueError("Torso not visible")
    p = (p - center) / scale
    result = []
    for a, b, c in JOINTS:
        u, v = p[a] - p[b], p[c] - p[b]
        result.append(float(np.arccos(np.clip(np.dot(u, v) /
                      max(np.linalg.norm(u) * np.linalg.norm(v), 1e-8), -1, 1)) / np.pi))
    return result
