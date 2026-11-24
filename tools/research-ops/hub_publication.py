"""Durable intent and restartable publication for one managed OKF hub.

The ledger CLI holds the project-state lock for each operation. Persist the
validated target before touching the live bundle. On restart only the recorded
base and target versions are admissible; do not guess at unexplained changes.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

from evidence import digest, file_sha, ident, require, verify_artifacts
from knowledge import HUB, PUBLISH, bundle_files, latest_publication, okf_precheck

BEGIN = 'begin-okf-publication'
PREPARE = 'prepare-okf-publication'
ABORT = 'abort-okf-publication'
ACTIONS = (BEGIN, PREPARE, PUBLISH, ABORT)
STAGING = Path('runtime/okf-staging')


def pending(state):
    return operation_state(state)[0]


def require_idle(state):
    if request := pending(state):
        raise ValueError(f"reconcile pending OKF publication {request['op_id']} first")


def view(state):
    request, prepared = operation_state(state)
    last = latest_publication(state)
    return {'pending': {'request_id': request['op_id'], 'staging': request['staging'],
                        'prepare_id': prepared['op_id'] if prepared else None} if request else None,
            'latest_publication': last['op_id'] if last else None}


def operation_state(state):
    rows = sorted((r for r in state['operations'].values() if r['group'] == 'lifecycle' and r['action'] in ACTIONS),
                  key=lambda r: r['revision'])
    request = prepared = None
    for row in rows:
        action = row['action']
        if action == BEGIN:
            require(not request and ident(row['op_id']) and row['staging'] == (STAGING / row['op_id']).as_posix() and
                    row['base_ledger_revision'] == row['revision'] - 1 and row['base_hub_sha256'] == digest(row['base_files']), 'invalid OKF publication ownership')
            request = row
        else:
            require(request and row['request_id'] == request['op_id'], 'invalid OKF publication request binding')
            if action == PREPARE:
                require(not prepared and row['hub_sha256'] == digest(row['target_files']), 'invalid OKF prepared target')
                prepared = row
            else:
                if action == PUBLISH:
                    require(prepared and row['prepare_id'] == prepared['op_id'] and all(
                        row[k] == prepared[k] for k in ('hub_sha256', 'writer_result', 'writer_artifacts')),
                        'invalid OKF publication checkpoint')
                else:
                    require(row['writer_state'] in ('terminated', 'not-dispatched'), 'invalid OKF abort observation')
                request = prepared = None
    return request, prepared


def markdown(paths):
    return {p: sha for p, sha in paths.items() if Path(p).suffix == '.md'}


def changed(base, target):
    return {p for p in base.keys() | target.keys() if base.get(p) != target.get(p)}


def scoped_paths(paths):
    require(isinstance(paths, list) and all(isinstance(p, str) and p == Path(p).as_posix() and
            not Path(p).is_absolute() and '..' not in Path(p).parts and Path(p).suffix == '.md' for p in paths) and
            len(paths) == len(set(paths)), 'authorize distinct bundle-relative Markdown paths')


def outside_bundle(project, artifacts):
    verify_artifacts(project, artifacts)
    for name in artifacts:
        path = (project / name).resolve()
        require(not path.is_relative_to(project / HUB) and not path.is_relative_to(project / STAGING),
                'keep publication evidence outside the live hub and staging trees')


def checked_stage(project, request, writer, artifacts):
    outside_bundle(project, request['request_artifacts'])
    require(isinstance(writer, str) and isinstance(artifacts, dict) and set(artifacts) == {writer},
            'pin the exact writer result outside the staging tree and hub')
    outside_bundle(project, artifacts)
    stage = project / request['staging']
    require(stage.resolve() == stage, 'cannot use a redirected OKF staging tree')
    target = bundle_files(stage)
    base = request['base_files']
    paths = changed(base, target)
    require(base.keys() <= target.keys() and paths <= set(request['paths']),
            'staged OKF bundle deletes files or changes paths outside the request')
    result = project / writer
    okf_precheck(stage, result)
    body = json.loads(result.read_text(encoding='utf-8'))
    updates = set(body['updated']) | set(body['deprecated'])
    require(set(body['created']) == paths - base.keys() and updates == paths & base.keys(),
            'writer result does not describe the exact staged diff')
    outside_bundle(project, artifacts)
    require(target == bundle_files(stage), 'staged OKF bytes changed while validating')
    return target


def fsync_dir(path):
    fd = os.open(path, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def replace_file(project, path, data):
    # Spill outside the hub so an interrupted replacement cannot leave stray
    # bundle files. Unexpected cross-filesystem layout fails instead of copying.
    fd, tmp = tempfile.mkstemp(prefix='.okf-publish-', dir=project)
    try:
        with os.fdopen(fd, 'wb') as out:
            if path.exists():
                os.fchmod(out.fileno(), stat.S_IMODE(path.stat().st_mode) & 0o777)
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def publish(project, request, prepared):
    writer, artifacts = prepared['writer_result'], prepared['writer_artifacts']
    base = request['base_files']
    target = checked_stage(project, request, writer, artifacts)
    require(target == prepared['target_files'], 'prepared OKF target changed; restore the pinned stage or reconcile')
    hub = project / HUB
    live = bundle_files(hub)
    paths = sorted(changed(base, target))
    require(all(live.get(p) in (base.get(p), target.get(p)) for p in live.keys() | base.keys() | target.keys()),
            'unexpected live OKF bytes; leave pending and reconcile before retrying')
    for name in paths:
        dest = hub / name
        require(dest.resolve() == dest, 'cannot publish through a redirected path')
        require(not dest.exists() or dest.is_file(), f'OKF destination is not a regular file: {name}')
        current = file_sha(dest) if dest.exists() else None
        if current == target[name]:
            continue
        require(current == base.get(name), f'live OKF path changed during publication: {name}')
        source = project / request['staging'] / name
        require(source.resolve() == source and source.is_file(), f'prepared OKF path is not a regular file: {name}')
        data = source.read_bytes()
        require(hashlib.sha256(data).hexdigest() == target[name], f'prepared OKF path changed: {name}')
        replace_file(project, dest, data)
    # Sync directory entries even for paths already present after an interrupted
    # attempt, and include any newly created parents up to the hub root.
    directories = {hub}
    for name in paths:
        directories.update(p for p in (hub / name).parents if p.is_relative_to(hub))
    for directory in sorted(directories, key=lambda p: (-len(p.parts), p.as_posix())):
        fsync_dir(directory)
    require(bundle_files(hub) == target, 'live OKF bundle does not match prepared checkpoint')
    okf_precheck(hub, project / writer)
    outside_bundle(project, artifacts)
    require(bundle_files(hub) == target, 'live OKF bundle changed during validation')
    return {'prepare_id': prepared['op_id'], 'hub_sha256': digest(target),
            'writer_result': writer, 'writer_artifacts': artifacts}


def advance(state, action, payload, project, op_id):
    request, prepared = operation_state(state)
    if action == BEGIN:
        require(not request, 'reconcile the pending OKF publication first')
        require(set(payload) == {'paths', 'request_artifacts'}, 'provide OKF paths and pinned request_artifacts')
        scoped_paths(payload['paths'])
        outside_bundle(project, payload['request_artifacts'])
        staging = project / STAGING / op_id
        require(staging.resolve() == staging and not staging.exists(), 'OKF staging must be a new project-local path')
        files = bundle_files(project / HUB)
        if last := latest_publication(state):
            old = state['operations'][last['prepare_id']]['target_files']
            require(markdown(files) == markdown(old), 'unmanaged Markdown drift; reconcile to the last OKF publication first')
        return {**payload, 'staging': staging.relative_to(project).as_posix(), 'base_ledger_revision': state['revision'],
                'base_files': files, 'base_hub_sha256': digest(files)}
    key = payload.get('request_id')
    require(request and key == request['op_id'], 'operation must name the pending OKF request')
    if action == PREPARE:
        require(not prepared and set(payload) == {'request_id', 'writer_result', 'writer_artifacts'},
                'prepare once with the exact writer result and artifact pin')
        require(bundle_files(project / HUB) == request['base_files'], 'live OKF base changed before prepare')
        target = checked_stage(project, request, payload['writer_result'], payload['writer_artifacts'])
        require(bundle_files(project / HUB) == request['base_files'], 'live OKF base changed during prepare')
        return {**payload, 'target_files': target, 'hub_sha256': digest(target)}
    if action == PUBLISH:
        require(prepared and set(payload) == {'request_id'}, 'prepare the OKF request before publishing')
        return {'request_id': key, **publish(project, request, prepared)}
    require(set(payload) == {'request_id', 'writer_state', 'recovery_artifacts'} and
            payload['writer_state'] in ('terminated', 'not-dispatched'),
            'pin verified writer exit or non-dispatch and recovery evidence')
    outside_bundle(project, payload['recovery_artifacts'])
    require(bundle_files(project / HUB) == request['base_files'],
            'cannot abort a changed or partially published hub; finish or restore the exact base and reconcile')
    return payload
