import numpy as np


def capture(layer, variant=0, count=60):
    duration = {"face": 3.8, "body": 4, "hand": 3}[layer]
    t = np.linspace(0, duration, count)
    phase = t / duration * 2 * np.pi
    if layer == "hand":
        values = np.column_stack([0.5 + 0.16 * np.cos(phase), 0.5 + 0.12 * np.sin(phase), np.zeros(count)])
        values[:, :2] += variant * 0.001
    elif layer == "body":
        values = np.column_stack([0.5 + 0.18 * np.sin(phase + i * 0.2 + variant * 0.01) for i in range(12)])
    else:
        values = np.column_stack([0.3 + 0.25 * np.sin(phase + i * 0.05 + variant * 0.01) for i in range(52)])
    result = {"times": (t * 1000).tolist(), "values": values.tolist()}
    if layer == "face":
        result["geometry"] = np.tile(np.linspace(0.2, 1.5, 60), (count, 1)).tolist()
    return result
