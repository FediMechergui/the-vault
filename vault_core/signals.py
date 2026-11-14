"""Signal primitives. Distances are normalized per sample and feature dimension."""
from __future__ import annotations

import numpy as np
from scipy.signal import savgol_filter


def matrix(values, minimum=8):
    x = np.asarray(values, dtype=float)
    if x.ndim != 2 or len(x) < minimum or not np.isfinite(x).all():
        raise ValueError(f"Expected at least {minimum} finite samples")
    return x


def smooth(x):
    x = matrix(x)
    return savgol_filter(x, 7, 2, axis=0, mode="interp")


def resample(x, count=64, times=None):
    x = matrix(x)
    t = np.linspace(0, 1, len(x)) if times is None else np.asarray(times, dtype=float)
    if len(t) != len(x) or not np.isfinite(t).all() or np.any(np.diff(t) <= 0):
        raise ValueError("Timestamps must be finite and strictly increasing")
    q = np.linspace(t[0], t[-1], count)
    return np.column_stack([np.interp(q, t, x[:, i]) for i in range(x.shape[1])])


def dtw(a, b, window=0.1):
    a, b = matrix(a), matrix(b)
    if a.shape[1] != b.shape[1]:
        raise ValueError("Feature dimensions differ")
    n, m = len(a), len(b)
    band = max(abs(n - m), int(np.ceil(max(n, m) * window)))
    costs = np.full((n + 1, m + 1), np.inf)
    lengths = np.zeros((n + 1, m + 1), dtype=int)
    costs[0, 0] = 0
    for i in range(1, n + 1):
        for j in range(max(1, i - band), min(m, i + band) + 1):
            choices = [(i - 1, j - 1), (i - 1, j), (i, j - 1)]
            u, v = min(choices, key=lambda p: costs[p])
            costs[i, j] = costs[u, v] + np.sqrt(np.mean((a[i - 1] - b[j - 1]) ** 2))
            lengths[i, j] = lengths[u, v] + 1
    return float(costs[n, m] / max(lengths[n, m], 1))


def unit_shape(x):
    x = matrix(x)
    x = x - x.mean(axis=0)
    scale = np.sqrt(np.mean(np.sum(x * x, axis=1)))
    if scale < 1e-5:
        raise ValueError("No meaningful movement detected")
    return x / scale


def procrustes_distance(a, b):
    a, b = unit_shape(resample(a)), unit_shape(resample(b))
    u, _, vt = np.linalg.svd(a.T @ b)
    correction = np.eye(a.shape[1])
    correction[-1, -1] = np.sign(np.linalg.det(u @ vt))
    rotation = u @ correction @ vt  # preserve handedness; no mirror acceptance
    return float(np.sqrt(np.mean(np.sum((a @ rotation - b) ** 2, axis=1))))


def cosine_distance(a, b):
    a, b = np.asarray(a), np.asarray(b)
    return float(np.clip(1 - np.dot(a, b) / max(np.linalg.norm(a) * np.linalg.norm(b), 1e-9), 0, 2))


class LandmarkFilter:
    """Constant-velocity Kalman filter; bridge at most two dropped frames."""

    def __init__(self):
        self.state = None
        self.covariance = np.eye(2)
        self.missing = 0

    def update(self, points, dt=1 / 15):
        if self.state is None:
            if points is None:
                return None
            self.state = np.stack([np.asarray(points, float), np.zeros_like(points, dtype=float)], axis=-1)
        transition = np.array([[1, dt], [0, 1]])
        self.state = self.state @ transition.T
        p = transition @ self.covariance @ transition.T + np.eye(2) * 0.0001
        if points is None:
            self.missing += 1
            self.covariance = p
            return self.state[..., 0].copy() if self.missing <= 2 else None
        self.missing = 0
        gain = p[:, 0] / (p[0, 0] + 0.001)
        self.state += (np.asarray(points) - self.state[..., 0])[..., None] * gain
        self.covariance = (np.eye(2) - np.outer(gain, [1, 0])) @ p
        return self.state[..., 0].copy()
