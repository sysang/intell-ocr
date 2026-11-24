#!/usr/bin/env python3
"""Reference analysis for paired applied-AI experiments; no model/API calls."""
import argparse
import csv
import json
import math
from pathlib import Path
import random
import statistics
import sys

from evidence import file_sha, require, text, verify_artifacts


VERSION = 'paired-bootstrap-v1'


def analyze(root, spec, observations):
    config = json.loads(spec.read_text())
    require(text(config.get('metric')) and text(config.get('baseline')) and text(config.get('candidate')) and
            config['baseline'] != config['candidate'] and text(config.get('limitation')), 'named metric, variants and limitation required')
    require(type(config.get('seed')) is int and type(config.get('samples')) is int and
            1000 <= config['samples'] <= 10000, 'explicit seed and 1000–10000 bootstrap draws required')
    verify_artifacts(root, config.get('inputs'))
    seen, differences = set(), []
    with observations.open(newline='', encoding='utf-8') as f:
        rows = csv.DictReader(f)
        require(rows.fieldnames == ['example_id', 'baseline', 'candidate'], 'expected paired CSV columns: example_id,baseline,candidate')
        for row in rows:
            pair_id = row['example_id']
            require(text(pair_id) and pair_id not in seen and None not in row, 'duplicate or malformed example')
            seen.add(pair_id)
            baseline, candidate = float(row['baseline']), float(row['candidate'])
            require(all(math.isfinite(x) and 0 <= x <= 1 for x in (baseline, candidate)), 'scores must be in [0, 1]')
            differences.append((pair_id, baseline, candidate))
            require(len(differences) <= 10000, 'reference analyzer supports up to 10000 pairs')
    require(bool(differences), 'no observations')
    differences.sort()
    scores = [c - b for _, b, c in differences]
    n = len(scores)
    rng = random.Random(config['seed'])
    draws = sorted(statistics.fmean(rng.choices(scores, k=n)) for _ in range(config['samples'])) if n >= 10 else []
    interval = [draws[math.floor((len(draws) - 1) * p)] for p in (0.025, 0.975)] if draws else None
    conclusion = ('interval-unavailable' if interval is None else 'interval-crosses-zero' if interval[0] <= 0 <= interval[1]
                  else 'candidate-higher' if interval[0] > 0 else 'baseline-higher')
    return {'analysis_version': VERSION, 'metric': config['metric'], 'baseline': config['baseline'], 'candidate': config['candidate'],
            'pairs': n, 'baseline_mean': statistics.fmean(b for _, b, _ in differences),
            'candidate_mean': statistics.fmean(c for _, _, c in differences), 'paired_mean_delta': statistics.fmean(scores),
            'percentile_interval_95': interval, 'comparison': conclusion, 'seed': config['seed'], 'draws': len(draws),
            'limitation': config['limitation'], 'inputs': config['inputs'],
            'raw_sha256': file_sha(observations), 'config_sha256': file_sha(spec), 'python_version': sys.version.split()[0]}


def draft(result):
    interval = result['percentile_interval_95']
    shown = 'not estimated for fewer than ten pairs' if interval is None else f'[{interval[0]:.4f}, {interval[1]:.4f}]'
    return (f"# Draft paired evaluation — {result['metric']}\n\n"
            f"**Observation:** For {result['pairs']} paired examples, the mean candidate-minus-baseline difference was "
            f"{result['paired_mean_delta']:+.4f}; paired bootstrap interval: {shown}.\n\n"
            f"**Scope limitation:** {result['limitation']}\n\n"
            f"**Action boundary:** This describes the frozen sample and metric only. Review assumptions, "
            f"failure modes, and generalizability before relying on it. This is not an Advisor verdict or a final report.\n\n"
            f"**Provenance:** raw SHA-256 `{result['raw_sha256']}`; config SHA-256 `{result['config_sha256']}`; "
            f"method `{result['analysis_version']}`, seed `{result['seed']}`.\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('config', type=Path)
    parser.add_argument('observations', type=Path)
    parser.add_argument('--format', choices=('json', 'draft'), default='json')
    args = parser.parse_args()
    try:
        result = analyze(args.root.resolve(), args.config, args.observations)
        print(json.dumps(result, indent=2) if args.format == 'json' else draft(result), end='\n')
        return 0
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
