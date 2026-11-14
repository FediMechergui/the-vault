"""Executable reference engine; MATLAB implements the same public JSON contract."""
from __future__ import annotations

from itertools import combinations
import numpy as np

from .signals import matrix, smooth, resample, dtw, unit_shape, procrustes_distance, cosine_distance

REPETITIONS = {"face": 2, "body": 3, "hand": 5}
BOUNDS = {"face": (0.025, 0.18), "body": (0.035, 0.22), "hand": (0.04, 0.32)}


def prepare(layer, capture):
    t = np.asarray(capture["times"], dtype=float) / 1000
    x = matrix(capture["values"])
    duration = float(t[-1] - t[0])
    if len(t) != len(x) or np.any(np.diff(t) <= 0) or not np.isfinite(t).all():
        raise ValueError("Invalid capture timing")
    min_duration, max_duration = {"face": (1.2, 4.5), "body": (3, 6.5), "hand": (0.7, 8)}[layer]
    if not min_duration <= duration <= max_duration:
        raise ValueError(f"Capture must last {min_duration:g}–{max_duration:g} seconds")
    if np.max(np.diff(t)) > 0.4:
        raise ValueError("Tracking lost for too long; please retry")
    count = max(8, int(round(duration * 15)))
    x = smooth(resample(x, count, t))
    if layer == "hand":
        if x.shape[1] != 3 or np.linalg.norm(np.ptp(x[:, :2], axis=0)) < 0.06:
            raise ValueError("Draw a larger signature")
        centered = unit_shape(x[:, :2])
        speed = np.linalg.norm(np.gradient(centered, duration / (len(x) - 1), axis=0), axis=1)
        acceleration = np.gradient(speed, duration / (len(x) - 1))
        dynamics = np.column_stack([speed / 10, acceleration / 100])
        return {"shape": resample(centered).tolist(), "signal": resample(dynamics).tolist(), "duration": duration}
    if layer == "body":
        if x.shape[1] != 12 or float(np.max(np.std(x, axis=0))) < 0.025:
            raise ValueError("Add a clear body movement")
        velocity = np.gradient(x, duration / (len(x) - 1), axis=0) / 5
        return {"signal": resample(np.column_stack([x, velocity])).tolist(), "duration": duration}
    if x.shape[1] != 52 or float(np.max(np.ptp(x, axis=0))) < 0.12:
        raise ValueError("Perform your two expressions clearly")
    geometry = matrix(capture["geometry"])
    if geometry.shape != (len(t), 60):
        raise ValueError("Invalid face geometry")
    return {"signal": resample(x).tolist(), "geometry": np.median(geometry, axis=0).tolist(), "duration": duration}


def distance(layer, a, b):
    temporal = dtw(a["signal"], b["signal"])
    if layer == "hand":
        return 0.4 * procrustes_distance(a["shape"], b["shape"]) + 0.6 * temporal
    if layer == "face":
        geometry = cosine_distance(a["geometry"], b["geometry"])
        return 0.45 * min(geometry * 10, 1) + 0.55 * temporal
    return temporal


def enroll(layer, captures):
    if layer not in REPETITIONS or len(captures) != REPETITIONS[layer]:
        raise ValueError("Incorrect number of repetitions")
    samples = [prepare(layer, c) for c in captures]
    distances = np.array([distance(layer, a, b) for a, b in combinations(samples, 2)])
    mu, sigma = float(distances.mean()), float(distances.std())
    low, high = BOUNDS[layer]
    if mu + 2 * sigma > high:
        raise ValueError("Repetitions are too different; record a more consistent gesture")
    threshold = float(np.clip(mu + 2 * sigma, low, high))
    return {"version": 1, "layer": layer, "samples": samples, "threshold": threshold, "mu": mu, "sigma": sigma}


def score(layer, capture, template, minimum_score=0.8):
    if template["layer"] != layer or template["version"] != 1:
        raise ValueError("Incompatible template")
    candidate = prepare(layer, capture)
    distances = [distance(layer, candidate, reference) for reference in template["samples"]]
    d = float(np.median(distances))
    ratio = d / template["threshold"]
    value = float(np.clip(1 - 0.2 * ratio, 0, 1))
    return {"score": value, "confidence": min(1.0, len(capture["times"]) / 30),
            "passed": bool(ratio <= 1 and value >= minimum_score),
            "details": {"distance": d, "threshold": template["threshold"], "ratio": ratio}}


def fuse_scores(results, weights=None):
    if not results:
        raise ValueError("At least one layer is required")
    weights = weights or {"face": 1, "body": 1, "hand": 1}
    total = sum(weights[r["layer"]] for r in results)
    return {"passed": all(r["passed"] for r in results),
            "score": sum(r["score"] * weights[r["layer"]] for r in results) / total}
