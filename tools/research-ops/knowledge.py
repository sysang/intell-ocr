"""Verify and bind required OKF checks to specific managed gate inputs."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote

from evidence import digest, file_sha, require, verify_artifacts

REPO = Path(__file__).resolve().parents[2]
WRITER = REPO / '.pi/agents/okf-writer/validate_okf.py'
READER = REPO / '.pi/agents/okf-reader/validate_result.py'
HUB = 'change-and-progress-logs'
ACTION = 'check-okf-gate'
PUBLISH = 'publish-okf'


def okf_precheck(root, result, reader=None, *, reader_required=False, snapshot=None):
    writer = WRITER
    commands = [([writer, 'bundle', root], None), ([writer, 'result', result], None)]
    if reader:
        commands.append(([READER], reader.read_text(encoding='utf-8')))
    reports = []
    for command, data in commands:
        p = subprocess.run([sys.executable, '-B', *(str(x) for x in command)], capture_output=True, text=True,
                           input=data, timeout=12)
        require(p.returncode == 0, (p.stdout or p.stderr)[-1500:])
        report = json.loads(p.stdout)
        require(report.get('valid') is True, 'OKF validator did not report a valid result')
        reports.append(report)
    body = json.loads(result.read_text(encoding='utf-8'))
    require(body['status'] == 'committed' and not body['revision']['git_commit_made'], 'writer has not published a clean result')
    if reader:
        retrieved = json.loads(reader.read_text(encoding='utf-8'))
        if reader_required:
            require(retrieved['status'] == 'sufficient' and retrieved['evidence'],
                    'required OKF reader did not supply sufficient primary evidence')
        else:
            require(retrieved['status'] != 'insufficient', 'OKF reader did not supply evidence')
        if snapshot is not None:
            require(retrieved['revision'].get('bundle_sha256') == snapshot,
                    'OKF reader result targets a different or unspecified hub snapshot')
        for item in retrieved['evidence']:
            path = (root / item['conceptPath']).resolve()
            require(path.is_relative_to(root) and path.is_file(),
                    f"reader references missing bundle file: {item['conceptPath']}")
    for name in set(body['created'] + body['updated'] + body['deprecated']):
        path = (root / name).resolve()
        require(path.is_relative_to(root) and path.is_file(), f'result references missing bundle file: {name}')
    links = set()
    for index in root.rglob('index.md'):
        for target in re.findall(r'^\s*[-*+]\s+\[[^\]]+\]\(([^)]+)\)', index.read_text(encoding='utf-8'), re.M):
            target = unquote(target.split('#', 1)[0])
            if ':' not in target and target:
                actual = (index.parent / target).resolve()
                require(actual.is_relative_to(root) and actual.exists(), f'broken or out-of-bundle index link: {target}')
                links.add(actual)
    for name in body['created']:
        if Path(name).suffix == '.md' and Path(name).name not in ('index.md', 'log.md'):
            require((root / name).resolve() in links, f'created concept missing from indexes: {name}')
    return {'checks': reports, 'created_files_checked': len(body['created'])}


def bundle_files(hub):
    require(hub.is_dir() and not hub.is_symlink(), 'expected a real project OKF hub')
    def unreadable(error):
        raise error  # A partial walk must never look like a complete checkpoint.

    files = {}
    for directory, children, names in os.walk(hub, onerror=unreadable):
        for entries, regular in ((children, False), (names, True)):
            for name in entries:
                path = Path(directory) / name
                relative = path.relative_to(hub).as_posix()
                require(not path.is_symlink(), f'cannot attest a symlink in the OKF bundle: {relative}')
                if regular:
                    require(path.is_file(), f'expected a regular file in the OKF bundle: {relative}')
                    files[relative] = file_sha(path)
    require(files, 'cannot attest an empty OKF hub')
    return files


def hub_fingerprint(project):
    return digest(bundle_files(project / HUB))


def validator_fingerprints(reader):
    files = [Path(__file__), Path(__file__).with_name('hub_publication.py'), WRITER, *([READER] if reader else [])]
    return {p.relative_to(REPO).as_posix(): file_sha(p) for p in files}


def required(manifest):
    return (manifest['phase'] in ('cycle', 'report') or manifest.get('okf_required') is True or
            manifest.get('okf_reader_required') is True)


def latest_publication(state):
    return max((r for r in state['operations'].values() if r['group'] == 'lifecycle' and r['action'] == PUBLISH),
               key=lambda r: r['revision'], default=None)


def require_publication(state, snapshot, publication_id):
    record = latest_publication(state)
    require(record and record['op_id'] == publication_id and record['hub_sha256'] == snapshot,
            'a current managed OKF publication for this exact hub snapshot is required')
    return record


def run_gate_check(state, project, manifest, payload):
    writer, reader, artifacts = (payload.get(k) for k in ('writer_result', 'reader_result', 'service_artifacts'))
    require(isinstance(writer, str) and (reader is None or isinstance(reader, str)) and reader != writer and
            isinstance(artifacts, dict) and set(artifacts) == ({writer, reader} if reader else {writer}),
            'pin the exact writer and applicable reader result files in service_artifacts')
    require(not manifest.get('okf_reader_required') or reader, 'this manifest requires a pinned OKF reader result')
    verify_artifacts(project, artifacts)
    snapshot = hub_fingerprint(project)
    require(payload.get('hub_sha256') == snapshot, 'OKF service evidence targets a different hub snapshot')
    publication = require_publication(state, snapshot, payload.get('publication_id'))
    require(publication['writer_result'] == writer and artifacts[writer] == publication['writer_artifacts'][writer],
            'writer evidence differs from the managed OKF publication')
    versions = validator_fingerprints(reader)
    result = okf_precheck(project / HUB, project / writer, project / reader if reader else None,
                          reader_required=manifest.get('okf_reader_required', False), snapshot=snapshot)
    verify_artifacts(project, artifacts)
    require(snapshot == hub_fingerprint(project) and versions == validator_fingerprints(reader),
            'OKF hub or validator changed while checking; reconcile and check again')
    return {'checked_manifest': digest(manifest), 'hub_sha256': snapshot, 'service_artifacts': artifacts,
            'publication_id': publication['op_id'], 'reader_checked': bool(reader), 'validators': versions, 'check_result': result}


def require_current(state, project, manifest, check_id):
    if not (required(manifest) or check_id):
        return
    check = state['operations'].get(check_id) if isinstance(check_id, str) else None
    require(check and check.get('action') == ACTION and check.get('group') == 'lifecycle' and
            check.get('cycle') == state['lifecycle']['outer_cycle'] and check.get('checked_manifest') == digest(manifest),
            'a passing OKF check for this exact manifest and cycle is required')
    require(not manifest.get('okf_reader_required') or check['reader_checked'], 'required OKF reader result was not checked')
    verify_artifacts(project, check['service_artifacts'])
    require(check['hub_sha256'] == hub_fingerprint(project), 'OKF hub changed since the required check')
    require_publication(state, check['hub_sha256'], check.get('publication_id'))
    require(check['validators'] == validator_fingerprints(check['reader_checked']), 'OKF validators changed since the required check')
