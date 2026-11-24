"""Mechanical checks for a tested implementation baseline; not scientific approval."""
import hashlib
from pathlib import PurePosixPath

import inner_attempts
from evidence import GIT_HASH, ident, require, verify_artifacts

UNCHANGED = {'interfaces', 'contracts', 'validity_assumptions'}


def required_tests(protocol):
    tests = protocol.get('required_tests')
    require(isinstance(tests, list) and tests and all(ident(x) for x in tests) and len(set(tests)) == len(tests),
            'the protocol manifest must name unique required test IDs')
    return set(tests)


def exact_revision(value):
    require(isinstance(value, str) and GIT_HASH.fullmatch(value), 'a full Git revision is required')
    return value


def baseline_path(name):
    if not isinstance(name, str):
        return False
    path = PurePosixPath(name)
    return (path.as_posix() == name and len(path.parts) >= 2 and path.parts[0] == 'src' and
            '..' not in path.parts)


def check_shape(manifest):
    info, artifacts = manifest.get('readiness'), manifest['artifacts']
    require(isinstance(info, dict) and set(info) == {'protocol_review', 'revision', 'baseline', 'tests'} and
            ident(info['protocol_review']), 'readiness must name the protocol review, revision, built baseline and tests')
    exact_revision(info['revision'])
    paths, tests = info['baseline'], info['tests']
    require(isinstance(paths, list) and paths and all(baseline_path(p) and p in artifacts for p in paths) and
            len(set(paths)) == len(paths), 'baseline files under src/ must be named and hashed in the manifest')
    require(isinstance(tests, dict) and tests, 'passing test observations are required')
    for name, result in tests.items():
        require(ident(name) and isinstance(result, dict) and set(result) == {'exit_code', 'output'} and
                type(result['exit_code']) is int and result['exit_code'] == 0 and
                isinstance(result['output'], str) and result['output'] in artifacts and result['output'] not in paths,
                f'test {name} needs a recorded zero exit code and a hashed output file')
    return info


def check_current(state, root, manifest, protocol_key, protocol):
    info = check_shape(manifest)
    require(info['protocol_review'] == protocol_key, 'readiness targets a different protocol approval')
    require(set(info['tests']) == required_tests(protocol), 'observations must cover exactly the approved required tests')
    revision = info['revision']
    inner_attempts.require_settled_writers(state, root)
    head = inner_attempts.head(root)
    inner_attempts.require_first_parent(root, revision, head)
    require(not inner_attempts.source_commits(root, revision, head), 'implementation has changed since the tested revision')
    inner_attempts.require_clean_source(root)
    prefix = inner_attempts.git(root, 'rev-parse', '--show-prefix').decode().rstrip('\n')
    for path in info['baseline']:
        blob = inner_attempts.git(root, 'cat-file', 'blob', f'{revision}:{prefix}{path}')
        require(hashlib.sha256(blob).hexdigest() == manifest['artifacts'][path],
                f'baseline is not the tested committed file: {path}')
    require(inner_attempts.head(root) == head, 'workspace HEAD changed during readiness checks')
    return info


def source_diff(root, before, after):
    before, after = exact_revision(before), exact_revision(after)
    inner_attempts.require_first_parent(root, before, after)
    return inner_attempts.git(root, 'diff', '--binary', '--no-ext-diff', '--no-textconv', '--no-color', '--no-renames',
                              before, after, '--', 'src/')


def check_reuse(state, root, original, current, proof):
    old, new = check_shape(original), check_shape(current)
    require(original.get('artifact_roles') == current.get('artifact_roles'),
            'readiness reuse must retain the reviewed package roles and their file bindings')
    require(old['protocol_review'] == new['protocol_review'] and old['revision'] != new['revision'],
            'reuse requires a later implementation revision within the same approved protocol')
    # Only covered baseline files may change under this exception. Other original evidence stays current.
    preserved = {p: h for p, h in original['artifacts'].items() if p not in old['baseline']}
    verify_artifacts(root, preserved)
    require(all(current['artifacts'].get(p) == h for p, h in preserved.items()),
            'reuse must retain the original non-baseline evidence')
    require(isinstance(proof, dict) and set(proof) == {'diff', 'unchanged'} and
            isinstance(proof['diff'], str) and proof['diff'] in current['artifacts'] and
            isinstance(proof['unchanged'], dict) and set(proof['unchanged']) == UNCHANGED and
            all(isinstance(p, str) and p in current['artifacts'] and p != proof['diff']
                for p in proof['unchanged'].values()),
            'reuse needs a hashed exact diff and evidence for unchanged interfaces, contracts and validity assumptions')
    diff = source_diff(root, old['revision'], new['revision'])
    require(diff and hashlib.sha256(diff).hexdigest() == current['artifacts'][proof['diff']],
            'supplied diff is not the exact implementation diff between the two revisions')
    prior_outputs = {t['output'] for t in old['tests'].values()}
    require(not (prior_outputs & {t['output'] for t in new['tests'].values()}),
            'reuse needs new per-attempt test observations, not the previously reviewed output files')
    commits = inner_attempts.source_commits(root, old['revision'], new['revision'])
    recorded = {commit for op in state['operations'].values() if op['group'] == 'lifecycle' and
                op['action'] == inner_attempts.INTEGRATE and op.get('cycle') == state['lifecycle']['outer_cycle']
                for commit in op['integration_commits']}
    require(set(commits) <= recorded, 'account for each integrated implementation change before reusing readiness')
