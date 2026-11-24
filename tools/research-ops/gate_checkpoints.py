"""Bind consequential lifecycle transitions to actual project Git commits."""
import hashlib
import json
from subprocess import TimeoutExpired

import gate_artifacts
import inner_attempts
import knowledge
from evidence import GIT_HASH, digest, file_sha, ident, require, text

ROUTE = 'gate-route'
HOLD = 'checkpoint-gate-hold'
REUSE = 'reuse-readiness'
START = 'start-planning'
ACTIONS = (START, ROUTE, HOLD, REUSE)
STATE = 'project-state.json'


def pending_hold(state):
    return next((key for key, r in state['gate_reviews'].items() if r.get('checkpoint_pending')), None)


def envelope(state, action, payload, op_id, root):
    """Build the decision to commit; it does not select or authorize a route."""
    require(action in ACTIONS and ident(op_id), 'checkpoint action and valid operation ID required')
    lc = state['lifecycle']
    cycle, plan = lc['outer_cycle'], lc['plan_version']
    base = {'project_id': state['identity']['project_id'], 'operation_id': op_id, 'action': action,
            'cycle': cycle, 'plan_version': plan,
            'inputs': {k: v for k, v in payload.items() if k not in ('checkpoint', 'okf_check')}}
    if action == START:
        require(text(payload.get('charter_ref')), 'provide the charter_ref for the opening cycle')
        base.update(gate='CYCLE_START', phase='planning', verdict='initialize', selected_route='planning',
                    resulting_cycle=cycle, charged_cycles=1 - state['budgets']['outer_cycles']['used'])
    else:
        key = payload.get('review_id' if action == REUSE else 'id')
        require(ident(key) and key in state['gate_reviews'], 'checkpoint must name the exact gate review')
        r = state['gate_reviews'][key]
        require(r['cycle'] == cycle, 'checkpoint must name a review in the current cycle')
        route = {HOLD: 'hold', REUSE: 'reuse-readiness'}.get(action, payload.get('route'))
        require(ident(route), 'name the selected route')
        require(action != HOLD or r.get('checkpoint_pending'), 'review does not have a pending HOLD checkpoint')
        require(action != HOLD or set(payload) <= {'id', 'checkpoint'}, 'HOLD checkpoint accepts only its review id')
        manifest = payload.get('manifest') if action == REUSE else r['manifest']
        base.update(gate=r['gate'], phase=r['phase'], verdict=r['verdict'], selected_route=route,
                    review_id=key, advisor_run_id=r.get('advisor_run_id'),
                    manifest_id=manifest.get('id') if isinstance(manifest, dict) else None,
                    manifest_sha256=digest(manifest), resulting_cycle=cycle + (route == 'replan'),
                    charged_cycles=int(route == 'replan'))
        if r['phase'] == 'cycle' and action == ROUTE:
            proposal = gate_artifacts.cycle_decision(manifest, root)
            require(text(payload.get('rationale')), 'record the rationale for the selected cycle route')
            base.update(id=proposal['id'], proposed_route=proposal['proposed_route'], rationale=payload['rationale'],
                        evidence_refs=proposal['evidence_refs'])
            if route == 'replan':
                base['next_plan'] = proposal['next_plan']
    label = f"{base['gate']} {base['verdict']}/{base['selected_route']} cycle {cycle}"
    leaf = 'cycle-decision.json' if base['phase'] == 'cycle' and action == ROUTE else 'decision.json'
    path = f'{knowledge.HUB}/decisions/checkpoints/{op_id}/{leaf}'
    return {'decision_path': path, 'git_subject': label, 'decision': base}


def previous_checkpoint(state, root, head):
    rows = [r for r in state['operations'].values() if 'decision_path' in r and
            r['group'] == 'lifecycle' and r['action'] in ACTIONS]
    if rows:
        latest = max(rows, key=lambda r: r['revision'])
        inner_attempts.require_first_parent(root, latest['checkpoint'], head)


def require_history(state, root):
    if any('decision_path' in r for r in state['operations'].values()):
        previous_checkpoint(state, root, inner_attempts.head(root))


def history_flags(state, root):
    try:
        require_history(state, root)
    except (ValueError, OSError, TimeoutExpired) as exc:
        return [str(exc)]
    return []


def checked_file(root, path):
    require(gate_artifacts.canonical_path(path), 'checkpoint paths must be canonical project-relative files')
    actual = root / path
    require(actual.resolve() == actual and actual.is_file(), f'checkpoint needs a regular project file: {path}')
    return actual


def strict_json(data):
    def unique_fields(pairs):
        result = {}
        for key, val in pairs:
            require(key not in result, f'checkpoint JSON repeats field {key}')
            result[key] = val
        return result

    return json.loads(data.decode('utf-8'), object_pairs_hook=unique_fields)


def check_blobs(root, commit, pins):
    prefix = inner_attempts.git(root, 'rev-parse', '--show-prefix').decode().rstrip('\n')
    relative = {prefix + path: pin for path, pin in pins.items()}
    raw = inner_attempts.git(root, '--literal-pathspecs', 'ls-tree', '-rz', '--full-tree', commit, '--', *relative)
    entries = {}
    for record in raw.split(b'\0'):
        if record:
            meta, path = record.split(b'\t', 1)
            mode, kind, oid = meta.decode('ascii').split()
            if kind == 'blob' and mode in ('100644', '100755'):
                entries[path.decode()] = oid
    for name, pin in relative.items():
        require(name in entries, f'checkpoint is missing tracked regular file: {name}')
        blob = inner_attempts.git(root, 'cat-file', 'blob', entries[name])
        require(hashlib.sha256(blob).hexdigest() == pin, f'checkpoint does not contain exact bytes: {name}')
    return prefix


def verify(state, action, payload, op_id, root, *, manifest=None, okf_check=None):
    info = envelope(state, action, payload, op_id, root)
    path = info['decision_path']
    head = inner_attempts.head(root)
    require(isinstance(payload.get('checkpoint'), str) and GIT_HASH.fullmatch(payload['checkpoint']) and
            payload['checkpoint'] == head, 'checkpoint must be the full current project Git HEAD')
    previous_checkpoint(state, root, head)
    subject = inner_attempts.git(root, 'show', '-s', '--format=%s', head).decode().strip()
    require(subject == info['git_subject'] or subject.startswith(info['git_subject'] + ', '),
            f"checkpoint commit subject must begin with: {info['git_subject']}")
    data = checked_file(root, STATE).read_bytes()
    require(digest(strict_json(data)) == digest(state), 'working ledger changed while checking the gate checkpoint')
    decision = checked_file(root, path).read_bytes()
    require(digest(strict_json(decision)) == digest(info['decision']), 'committed decision must describe the exact selected transition')
    pins = {STATE: hashlib.sha256(data).hexdigest(), path: hashlib.sha256(decision).hexdigest()}
    if action == START:
        charter = payload['charter_ref']
        pins[charter] = file_sha(checked_file(root, charter))
    if manifest is not None:
        paths = list(manifest['artifact_roles'].values())
        if manifest['phase'] == 'readiness':
            paths.extend(manifest['readiness']['baseline'])
            paths.extend(t['output'] for t in manifest['readiness']['tests'].values())
        for name in paths:
            require(name not in pins or pins[name] == manifest['artifacts'][name], 'checkpoint pins conflict with the reviewed manifest')
            pins[name] = manifest['artifacts'][name]
        if action == REUSE:
            proof = payload['proof']
            for name in [proof['diff'], *proof['unchanged'].values()]:
                pins[name] = manifest['artifacts'][name]
    if action == ROUTE and payload.get('route') == 'stop':
        name = payload['status_report']
        pins[name] = file_sha(checked_file(root, name))
    hub_paths = None
    if okf_check:
        check = state['operations'][okf_check]
        bundle = knowledge.bundle_files(root / knowledge.HUB)
        require(digest(bundle) == check['hub_sha256'], 'OKF bundle changed after the gate check')
        hub_paths = {f'{knowledge.HUB}/{name}': pin for name, pin in bundle.items()}
        require(all(p not in pins or pins[p] == pin for p, pin in hub_paths.items()), 'checkpoint pins conflict with the OKF bundle')
        pins.update(hub_paths)
        for name, pin in check['service_artifacts'].items():
            require(name not in pins or pins[name] == pin, 'checkpoint pins conflict with OKF service evidence')
            pins[name] = pin
    prefix = check_blobs(root, head, pins)
    if hub_paths is not None:
        tracked = inner_attempts.git(root, '--literal-pathspecs', 'ls-tree', '-rz', '--name-only', '--full-tree',
                                     head, '--', f'{prefix}{knowledge.HUB}').decode().split('\0')
        require({p for p in tracked if p} == {prefix + p for p in hub_paths},
                'Git checkpoint hub tree differs from the exact verified bundle')
    require(all(file_sha(checked_file(root, name)) == pin for name, pin in pins.items()) and
            inner_attempts.head(root) == head, 'working files or HEAD changed while verifying the checkpoint')
    return {k: info['decision'][k] for k in ('gate', 'phase', 'verdict', 'selected_route', 'cycle',
            'resulting_cycle', 'charged_cycles')} | {'checkpoint': head, 'decision_path': path, 'decision_sha256': pins[path]}