#!/usr/bin/env python3
"""Deterministic pre-gate checks; results are evidence, not verdicts."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote

from evidence import FIXED, date, digest, file_sha, ident, require, text, texts
from gates import check_manifest, validate_verdict
from ledger import check_invariants, load_state, now_iso

REPO = Path(__file__).resolve().parents[2]


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def manifest(root, args):
    files = {}
    for name in sorted(set(args.paths)):
        path = (root / name).resolve(strict=True)
        require(path.is_relative_to(root) and path.is_file(), f'outside project or not a file: {name}')
        files[path.relative_to(root).as_posix()] = file_sha(path)
    result = {'id': args.id, 'gate': args.gate, 'phase': args.phase, 'artifacts': files}
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


def okf_precheck(root, result, reader=None):
    writer = REPO / '.pi/agents/okf-writer/validate_okf.py'
    commands = [([writer, 'bundle', root], None), ([writer, 'result', result], None)]
    if reader:
        commands.append(([REPO / '.pi/agents/okf-reader/validate_result.py'], reader.read_text()))
    reports = []
    for command, data in commands:
        p = subprocess.run([sys.executable, '-B', *(str(x) for x in command)], capture_output=True, text=True,
                           input=data, timeout=12)
        require(p.returncode == 0, (p.stdout or p.stderr)[-1500:])
        reports.append(json.loads(p.stdout))
    body = load(result)
    require(body['status'] == 'committed' and not body['revision']['git_commit_made'], 'writer has not published a clean result')
    for name in set(body['created'] + body['updated'] + body['deprecated']):
        path = (root / name).resolve()
        require(path.is_relative_to(root) and path.is_file(), f'result references missing bundle file: {name}')
    links = set()
    for index in root.rglob('index.md'):
        for target in re.findall(r'^\s*[-*+]\s+\[[^\]]+\]\(([^)]+)\)', index.read_text(), re.M):
            target = unquote(target.split('#', 1)[0])
            if ':' not in target and target:
                actual = (index.parent / target).resolve()
                require(actual.is_relative_to(root) and actual.exists(), f'broken or out-of-bundle index link: {target}')
                links.add(actual)
    for name in body['created']:
        if Path(name).suffix == '.md' and Path(name).name not in ('index.md', 'log.md'):
            require((root / name).resolve() in links, f'created concept missing from indexes: {name}')
    return {'checks': reports, 'created_files_checked': len(body['created'])}


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
        elif a.command == 'validate-verdict':
            m = load(a.manifest)
            check_manifest(m, a.gate, a.phase, a.root)
            output = {'valid': True, 'verdict': validate_verdict(load(a.verdict), a.gate, m['id'])}
        elif a.command == 'verdict-still-covers':
            output = coverage(a.root, load(a.reviewed), load(a.current))
        elif a.command == 'okf-gate-precheck':
            output = okf_precheck(a.root.resolve(), a.writer_result, a.reader_result)
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
