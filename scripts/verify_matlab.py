"""Run real MATLAB tests and compare synthetic scoring against the Python reference."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'matlab-engine')]
from matlab_host import open_engine, prepare_engine, select_backend
from tests.samples import capture
from vault_core.scoring import REPETITIONS, enroll, score


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matlab-root')
    parser.add_argument('--output', default='docs/matlab-smoke.json')
    args = parser.parse_args()
    _, installation = select_backend('matlab-engine', args.matlab_root)
    if os.getenv('VAULT_ENGINE_PREPARED') != str(installation.root):
        env = prepare_engine(installation, ROOT)
        env['VAULT_ENGINE_PREPARED'] = str(installation.root)
        return subprocess.call([sys.executable, __file__, *sys.argv[1:]], env=env, cwd=ROOT)
    engine, details = open_engine()
    report = {'engine': 'matlab-engine', **details, 'input': 'synthetic test signals; not a biometric study', 'layers': {}}
    try:
        tests = str(ROOT / 'matlab-engine/tests').replace("'", "''")
        result = engine.eval(f"jsonencode(struct('passed',sum([runtests('{tests}').Passed])))", nargout=1)
        report['matlab_unit_tests_passed'] = json.loads(result)['passed']
        if report['matlab_unit_tests_passed'] != 3:
            raise AssertionError('MATLAB unit tests did not all pass')
        for layer, repetitions in REPETITIONS.items():
            captures = [capture(layer, i) for i in range(repetitions)]
            template = json.loads(engine.vaulte_engine(json.dumps({'operation': 'enroll', 'layer': layer, 'captures': captures}), nargout=1))['template']
            reference = enroll(layer, captures)
            errors = [abs(template[k] - reference[k]) for k in ('mu', 'sigma', 'threshold')]
            timings = []
            for variant in (0, 1, 30):
                sample = capture(layer, variant)
                before = time.perf_counter()
                actual = json.loads(engine.vaulte_engine(json.dumps({'operation': 'score', 'layer': layer, 'capture': sample,
                    'template': template, 'minimum_score': 0.8}), nargout=1))
                timings.append((time.perf_counter() - before) * 1000)
                expected = score(layer, sample, reference)
                errors.append(abs(actual['score'] - expected['score']))
                errors.append(abs(actual['details']['distance'] - expected['details']['distance']))
                assert actual['passed'] == expected['passed'], (layer, variant, actual, expected)
            maximum = max(errors)
            assert maximum < 1e-8, (layer, maximum)
            report['layers'][layer] = {'cases': 3, 'maximum_absolute_difference': maximum, 'decision_ms': timings}
    finally:
        engine.quit()
    path = ROOT / args.output
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
