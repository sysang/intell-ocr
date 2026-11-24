#!/usr/bin/env python3
"""Deterministic pre-gate checks; results are evidence, not verdicts."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

from evidence import FIXED, date, digest, file_sha, ident, require, text, texts
from gates import check_manifest, validate_verdict
from knowledge import hub_fingerprint, okf_precheck
from ledger import check_invariants, load_state, now_iso
from readiness import source_diff


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def manifest(root, args):
    files = {}
    for name in sorted(set(args.paths)):
        path = (root / name).resolve(strict=True)
        require(path.is_relative_to(root) and path.is_file(), f'outside project or not a file: {name}')
        files[path.relative_to(root).as_posix()] = file_sha(path)
    result = {'id': args.id, 'gate': args.gate, 'phase': args.phase, 'artifacts': files}
    if args.phase == 'protocol':
        result['required_tests'] = args.required_test
    elif args.phase == 'readiness':
        require(args.readiness_evidence, 'pass --readiness-evidence with the readiness JSON object')
        result['readiness'] = load(args.readiness_evidence)
    check_manifest(result, args.gate, args.phase, root)
    return result


def coverage(root, reviewed, current):
    check_manifest(current, current['gate'], current['phase'], root)
    require((reviewed['gate'], reviewed['phase']) == (current['gate'], current['phase']), 'different gate or phase')
    before, after = reviewed['artifacts'], current['artifacts']
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    metadata_changed = {k: v for k, v in reviewed.items() if k not in ('artifacts', 'id')} != {
        k: v for k, v in current.items() if k not in ('artifacts', 'id')}
    return {'covers_same_bytes': not (changed or metadata_changed), 'changed': changed, 'metadata_changed': metadata_changed}


def pool_profile(approval, observation):
    """Compare observed resolution to operator approval; does not discover runtime tools."""
    require(text(approval.get('operator')) and isinstance(approval.get('profile'), dict), 'operator approval required')
    approved = approval['profile']
    fields = {'name', 'definition_sha256', 'model', 'override_source', 'tools', 'indirect_tools', 'model_endpoints'}
    require(set(approved) == set(observation) == fields, 'complete exact approved and observed profiles required')
    normalized = []
    for profile in (approved, observation):
        require(ident(profile['name']) and profile['name'] not in FIXED and profile['name'] != 'research-lead' and
                text(profile['definition_sha256']) and re.fullmatch('[0-9a-f]{64}', profile['definition_sha256']) and
                text(profile['model']) and '/' in profile['model'] and text(profile['override_source']), 'unresolved pool identity or model')
        capabilities = ('tools', 'indirect_tools', 'model_endpoints')
        require(all(texts(profile[k]) and len(set(profile[k])) == len(profile[k]) for k in capabilities),
                'capability inventory must be explicit and unambiguous')
        require(not any(t.startswith(('subagent', 'contact_supervisor', 'bd_', 'tool_search', 'bg_wait'))
                        for t in profile['tools'] + profile['indirect_tools']), 'pool profile reaches a prohibited tool')
        normalized.append({**profile, **{k: sorted(profile[k]) for k in capabilities}})
    require(normalized[0] == normalized[1], 'pool profile drift: reapproval required before launch')
    return {'matches': True, 'profile_sha256': digest(normalized[0]),
            'scope': 'comparison of supplied records, not proof of runtime confinement'}


def freshness(state_path, snapshot, now):
    s = load_state(state_path)
    problems = check_invariants(s)
    require(not problems, '; '.join(problems))
    flags = []
    if s.get('revision') != snapshot.get('state_revision'):
        flags.append('snapshot differs from current ledger revision')
    if date(snapshot['as_of']) > date(now):
        flags.append('snapshot timestamp is in the future')
    for name, item in snapshot.get('stale_after', {}).items():
        if date(now) >= date(item):
            flags.append(f'{name}: stale_after reached')
    return {'flags': flags, 'checked_at': now, 'state_revision': s.get('revision')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    m = sub.add_parser('manifest')
    m.add_argument('root', type=Path)
    m.add_argument('gate')
    m.add_argument('phase')
    m.add_argument('id')
    m.add_argument('paths', nargs='+')
    m.add_argument('--required-test', action='append', default=[])
    m.add_argument('--readiness-evidence', type=Path)
    p = sub.add_parser('readiness-diff')
    p.add_argument('root', type=Path)
    p.add_argument('before')
    p.add_argument('after')
    p = sub.add_parser('validate-verdict')
    p.add_argument('root', type=Path)
    p.add_argument('gate')
    p.add_argument('phase')
    p.add_argument('manifest', type=Path)
    p.add_argument('verdict', type=Path)
    p = sub.add_parser('verdict-still-covers')
    p.add_argument('root', type=Path)
    p.add_argument('reviewed', type=Path)
    p.add_argument('current', type=Path)
    p = sub.add_parser('okf-gate-precheck')
    p.add_argument('root', type=Path)
    p.add_argument('writer_result', type=Path)
    p.add_argument('--reader-result', type=Path)
    p = sub.add_parser('okf-hub-snapshot')
    p.add_argument('project', type=Path)
    p = sub.add_parser('freshness-flags')
    p.add_argument('state', type=Path)
    p.add_argument('snapshot', type=Path, help='JSON containing as_of, state_revision, and optional stale_after map')
    p.add_argument('--now')
    p = sub.add_parser('check-pool-profile')
    p.add_argument('approval', type=Path)
    p.add_argument('observation', type=Path)
    a = parser.parse_args()
    try:
        if a.command == 'manifest':
            output = manifest(a.root.resolve(), a)
        elif a.command == 'readiness-diff':
            sys.stdout.buffer.write(source_diff(a.root.resolve(), a.before, a.after))
            return 0
        elif a.command == 'validate-verdict':
            m = load(a.manifest)
            check_manifest(m, a.gate, a.phase, a.root)
            output = {'valid': True, 'verdict': validate_verdict(load(a.verdict), a.gate, m['id'])}
        elif a.command == 'verdict-still-covers':
            output = coverage(a.root, load(a.reviewed), load(a.current))
        elif a.command == 'okf-gate-precheck':
            output = okf_precheck(a.root.resolve(), a.writer_result, a.reader_result)
        elif a.command == 'okf-hub-snapshot':
            output = {'hub_sha256': hub_fingerprint(a.project.resolve())}
        elif a.command == 'check-pool-profile':
            output = pool_profile(load(a.approval), load(a.observation))
        else:
            output = freshness(a.state, load(a.snapshot), a.now or now_iso())
        print(json.dumps(output, indent=2))
        return 0
    except (OSError, ValueError, KeyError, AttributeError, TypeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({'valid': False, 'errors': [str(exc)]}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
