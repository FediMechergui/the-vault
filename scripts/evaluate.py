"""Compute per-layer ROC/EER and latency from consented, held-out trials.

CSV columns: layer,genuine,score,latency_ms. genuine must be 0 or 1.
No fabricated volunteer data or claimed performance is bundled with this project.
"""
import argparse
import csv
import json
from pathlib import Path
import numpy as np


def metrics(scores, genuine):
    scores, genuine = np.asarray(scores, float), np.asarray(genuine, bool)
    if not len(scores) or not genuine.any() or genuine.all() or not np.isfinite(scores).all():
        raise ValueError('Each layer needs finite genuine and impostor scores')
    if np.any((scores < 0) | (scores > 1)):
        raise ValueError('Scores must be in [0, 1]')
    thresholds = np.r_[-1e-9, np.unique(scores), 1 + 1e-9]
    far = np.array([(scores[~genuine] >= t).mean() for t in thresholds])
    frr = np.array([(scores[genuine] < t).mean() for t in thresholds])
    i = int(np.argmin(np.abs(far - frr)))
    return {'eer_estimate': float((far[i] + frr[i]) / 2), 'threshold': float(thresholds[i]),
            'genuine_trials': int(genuine.sum()), 'impostor_trials': int((~genuine).sum()),
            'far_at_080': float((scores[~genuine] >= .8).mean()),
            'frr_at_080': float((scores[genuine] < .8).mean()),
            'roc': [{'threshold': float(t), 'far': float(a), 'frr': float(b)} for t, a, b in zip(thresholds, far, frr)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('--output', type=Path, default=Path('.local/evaluation.json'))
    args = parser.parse_args()
    with args.csv.open(newline='') as file:
        rows = list(csv.DictReader(file))
    report = {}
    for layer in ('face', 'body', 'hand'):
        subset = [r for r in rows if r['layer'] == layer]
        if not subset: continue
        if any(r['genuine'] not in ('0', '1') for r in subset):
            raise ValueError('genuine must be 0 or 1')
        report[layer] = metrics([float(r['score']) for r in subset], [r['genuine'] == '1' for r in subset])
        latency = [float(r['latency_ms']) for r in subset]
        report[layer]['latency_p50_ms'] = float(np.percentile(latency, 50))
        report[layer]['latency_p95_ms'] = float(np.percentile(latency, 95))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(f'Evaluation written to {args.output}; scores must be from held-out participants/trials.')


if __name__ == '__main__': main()
