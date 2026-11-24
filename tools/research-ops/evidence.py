"""Durable Worker/pool evidence, not a backlog. All writes use ledger.py."""
import copy
import hashlib
import json
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')
TASK_ID = re.compile(r'[a-z][a-z0-9]*-[a-zA-Z0-9][a-zA-Z0-9-]{0,119}\Z')
GIT_HASH = re.compile(r'(?:[0-9a-f]{40}|[0-9a-f]{64})\Z')
KINDS = ('briefs', 'attempts', 'results', 'decisions', 'availability', 'uses', 'drops')
TERMINAL = {'terminated', 'not_dispatched'}
FIXED = {'research-advisor', 'engineering-worker', 'harness-architector', 'backend-architector',
         'frontend-architector', 'okf-reader', 'okf-writer'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def ident(value):
    return isinstance(value, str) and bool(ID.fullmatch(value))


def texts(value):
    return isinstance(value, list) and all(text(x) for x in value)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def date(value):
    result = datetime.fromisoformat(value)
    require(result.utcoffset() is not None, 'deadline requires a time zone')
    return result


def empty():
    return {name: {} for name in KINDS}


def find(db, kind, key):
    require(ident(key) and key in db[kind], f'unknown {kind} ID: {key!r}')
    return db[kind][key]


def add(db, kind, key, value, now):
    require(ident(key) and not any(key in db[k] for k in KINDS), 'ID invalid or already in use')
    db[kind][key] = {**value, 'id': key, 'recorded_at': now}
    return key


def active_brief(db, assignment):
    revisions = [x for x in db['briefs'].values() if x['assignment_id'] == assignment]
    replaced = {x.get('previous_revision') for x in revisions}
    return next((x for x in revisions if x['id'] not in replaced), None)


def current_decision(db, key):
    return not any(x.get('supersedes') == key for x in db['decisions'].values())


def invalid_consumers(db):
    invalid = set()
    changed = True
    while changed:
        size = len(invalid)
        for use in db['uses'].values():
            d = db['decisions'][use['decision_id']]
            if not current_decision(db, d['id']) or d['revision_id'] in invalid:
                invalid.add(use['consumer'])
        changed = size != len(invalid)
    return invalid


def usable(db, decision):
    return (decision['verdict'] == 'accepted' and current_decision(db, decision['id']) and
            decision['revision_id'] not in invalid_consumers(db) and
            any(x['decision_id'] == decision['id'] for x in db['availability'].values()))


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def verify_artifacts(root, artifacts):
    require(isinstance(artifacts, dict) and bool(artifacts), 'nonempty artifact hash map required')
    root = root.resolve()
    for name, sha in artifacts.items():
        require(text(name) and not Path(name).is_absolute() and '..' not in Path(name).parts and
                isinstance(sha, str) and re.fullmatch('[0-9a-f]{64}', sha), 'invalid artifact reference')
        path = (root / name).resolve(strict=True)
        require(path.is_relative_to(root) and path.is_file(), 'artifact must be a project file')
        require(file_sha(path) == sha, f'artifact drift: {name}')


def check_consumer(db, key, root):
    require(key not in invalid_consumers(db), 'consumer needs revalidation after supersession')
    pending, visited = [key], set()
    while pending:
        consumer = pending.pop()
        if consumer in visited:
            continue
        visited.add(consumer)
        for use in db['uses'].values():
            if use['consumer'] == consumer:
                d = find(db, 'decisions', use['decision_id'])
                require(usable(db, d), 'pinned acceptance unavailable')
                available = next(x for x in db['availability'].values() if x['decision_id'] == d['id'])
                verify_artifacts(root, {use['output']: available['artifacts'][use['output']]})
                pending.append(d['revision_id'])


def close_check(state, task_id, record_id, disposition, root):
    require(state['lifecycle']['status'] == 'active', 'project is not active')
    db = state['execution']
    if disposition == 'dropped':
        drop = find(db, 'drops', record_id)
        require(drop['beads_task_id'] == task_id, 'drop does not belong to this task')
        return
    d = find(db, 'decisions', record_id)
    brief = find(db, 'briefs', d['revision_id'])
    require(brief['beads_task_id'] == task_id and active_brief(db, brief['assignment_id']) == brief and
            usable(db, d), 'no usable acceptance for this task')
    check_consumer(db, d['revision_id'], root)
    available = next(x for x in db['availability'].values() if x['decision_id'] == record_id)
    verify_artifacts(root, available['artifacts'])


def attempt_open(a):
    return a['execution'] not in TERMINAL or a['effects'] == 'unreconciled'


def view(db):
    return {'open_attempts': [a for a in db['attempts'].values() if attempt_open(a)],
            'pending_verification': [r['id'] for r in db['results'].values()
                                     if not any(d.get('result_id') == r['id'] for d in db['decisions'].values())],
            'pending_availability': [d['id'] for d in db['decisions'].values()
                                     if d['verdict'] == 'accepted' and current_decision(db, d['id'])
                                     and not any(x['decision_id'] == d['id'] for x in db['availability'].values())],
            'revalidate': sorted(invalid_consumers(db))}


def transition(state, action, p, now, root):
    """Apply one named operation to a working copy; no I/O except evidence checks."""
    require(isinstance(p, dict), 'operation input must be an object')
    db = state['execution']
    key = p.get('id')
    if action in ('issue', 'mark-ready', 'reserve'):
        require(state['lifecycle']['status'] == 'active' and state['lifecycle']['stage'] != 'COMPLETED',
                'project is not active')
    if action == 'issue':
        required = ('assignment_id', 'beads_task_id', 'assignee', 'mode', 'scope', 'deliverable',
                    'criteria', 'exclusions', 'source_versions', 'read_paths', 'modify_paths',
                    'commands', 'external_actions', 'tools', 'attempt_limit', 'soft_seconds', 'hard_seconds')
        require(set(required) <= p.keys() and not p.keys() - {*required, 'id', 'previous_revision',
                'base_revision', 'verification_exemption', 'routing_reason', 'assessment_id'}, 'incomplete brief or unknown fields')
        require(ident(p['assignment_id']) and isinstance(p['beads_task_id'], str) and
                TASK_ID.fullmatch(p['beads_task_id']) and ident(p['assignee']), 'invalid brief identifiers')
        require(p['assignee'] == 'engineering-worker' or
                (p['assignee'] not in FIXED and text(p.get('routing_reason'))), 'not a Worker/justified pool assignment')
        require(text(p['scope']) and text(p['deliverable']) and texts(p['criteria']) and p['criteria'], 'missing brief criteria')
        require(isinstance(p['source_versions'], dict) and p['source_versions'] and
                all(text(k) and text(v) for k, v in p['source_versions'].items()), 'pinned sources required')
        require(all(texts(p[k]) for k in ('exclusions', 'read_paths', 'modify_paths', 'commands', 'external_actions', 'tools')),
                'brief grants must be lists of strings')
        require(p['mode'] in ('read', 'execute', 'write') and
                (p['mode'] == 'write' or not p['modify_paths']) and
                (p['mode'] != 'read' or not (p['commands'] or p['external_actions'])), 'invalid mode/grants')
        require(all(type(p[k]) is int and p[k] > 0 for k in ('attempt_limit', 'soft_seconds', 'hard_seconds')) and
                p['soft_seconds'] < p['hard_seconds'], 'invalid attempt or time budget')
        if p['mode'] != 'read':
            require(text(p.get('base_revision')) and GIT_HASH.fullmatch(p['base_revision']) and
                    (p['commands'] or text(p.get('verification_exemption'))),
                    'base revision and commands or exemption required')
        prior = active_brief(db, p['assignment_id'])
        require(not any(b['beads_task_id'] == p['beads_task_id'] and b['assignment_id'] != p['assignment_id']
                        for b in db['briefs'].values()), 'task already has an assignment')
        if prior:
            require(p.get('previous_revision') == prior['id'] and p['beads_task_id'] == prior['beads_task_id'] and
                    p['attempt_limit'] == prior['attempt_limit'], 'new revision must keep task and attempt budget')
            require(not any(a['assignment_id'] == p['assignment_id'] and attempt_open(a)
                            for a in db['attempts'].values()), 'reconcile prior attempt before revising')
        else:
            require(p.get('previous_revision') is None, 'first revision has no predecessor')
        add(db, 'briefs', key, {**p, 'ready': None}, now)
    elif action == 'mark-ready':
        b = find(db, 'briefs', key)
        require(active_brief(db, b['assignment_id']) == b and not b['ready'] and
                key not in invalid_consumers(db) and text(p.get('basis')), 'fresh readiness basis required')
        check_consumer(db, key, root)
        b['ready'] = {'basis': p['basis'], 'recorded_at': now}
    elif action == 'reserve':
        b = find(db, 'briefs', p.get('revision_id'))
        require(b['ready'] and active_brief(db, b['assignment_id']) == b and b['id'] not in invalid_consumers(db),
                'active READY revision required')
        check_consumer(db, b['id'], root)
        require(text(p.get('profile_ref')), 'verified profile reference required')
        require(not any(d['revision_id'] == b['id'] for d in db['drops'].values()), 'revision was dropped')
        require(not any(d['revision_id'] == b['id'] and usable(db, d) for d in db['decisions'].values()),
                'revision already has available acceptance')
        require(not any(d['revision_id'] == b['id'] and d['verdict'] == 'accepted' and current_decision(db, d['id'])
                        for d in db['decisions'].values()), 'reconcile existing acceptance before retry')
        attempts = [a for a in db['attempts'].values() if a['assignment_id'] == b['assignment_id']]
        require(not any(attempt_open(a) for a in attempts), 'prior attempt or effects unresolved')
        require(sum(a['execution'] != 'not_dispatched' for a in attempts) < b['attempt_limit'], 'attempt budget exhausted')
        workspace = p.get('workspace')
        if b['mode'] != 'read':
            require(text(workspace) and Path(workspace).is_absolute(), 'absolute workspace required')
            workspace = str(Path(workspace).resolve(strict=True))
            head = subprocess.run(['git', '-C', workspace, 'rev-parse', '--verify', 'HEAD'],
                                  capture_output=True, text=True, timeout=10)
            require(head.returncode == 0 and head.stdout.strip() == b['base_revision'], 'workspace HEAD does not match base revision')
            require(not any(a['workspace'] and attempt_open(a) and
                            (Path(a['workspace']).is_relative_to(workspace) or Path(workspace).is_relative_to(a['workspace']))
                            for a in db['attempts'].values()), 'workspace still owned by an unresolved attempt')
        else:
            require(workspace is None, 'read-only attempt cannot claim a write workspace')
        add(db, 'attempts', key, {'assignment_id': b['assignment_id'], 'revision_id': b['id'],
            'workspace': workspace, 'profile_ref': p['profile_ref'], 'execution': 'dispatch_pending',
            'soft_deadline': (date(now) + timedelta(seconds=b['soft_seconds'])).isoformat(),
            'hard_deadline': (date(now) + timedelta(seconds=b['hard_seconds'])).isoformat(),
            'effects': 'unreconciled' if workspace else 'none', 'run_id': None, 'cutoff': None, 'no_result': None}, now)
    elif action in ('launch-unknown', 'attach-run', 'prove-non-dispatch', 'observe-termination', 'hard-cutoff',
                    'record-no-result', 'reconcile-effects'):
        a = find(db, 'attempts', key)
        require(text(p.get('evidence')), 'record exact runtime or reconciliation evidence')
        proof = p['evidence']
        if action == 'launch-unknown':
            require(a['execution'] == 'dispatch_pending', 'only an unbound fresh intent may become unknown')
            a['execution'] = 'launch_unknown'
        elif action == 'attach-run':
            run = p.get('run_id')
            require(a['execution'] in ('dispatch_pending', 'launch_unknown') and ident(run) and
                    not any(x['run_id'] == run for x in db['attempts'].values()), 'invalid or duplicate run binding')
            a.update(execution='dispatched', run_id=run)
        elif action == 'prove-non-dispatch':
            require(a['execution'] in ('dispatch_pending', 'launch_unknown'), 'cannot release a bound or settled run')
            a.update(execution='not_dispatched', effects='none')
        elif action == 'observe-termination':
            require(a['execution'] == 'dispatched', 'bind the exact run before recording termination')
            a['execution'] = 'terminated'
        elif action == 'hard-cutoff':
            require(a['execution'] != 'not_dispatched' and not a['cutoff'] and
                    not any(r['attempt_id'] == key and not r['late'] for r in db['results'].values()), 'cutoff is not applicable')
            a['cutoff'] = now
            a['no_result'] = proof
        elif action == 'record-no-result':
            require(a['execution'] == 'terminated' and not a['no_result'] and
                    not any(r['attempt_id'] == key and not r['late'] for r in db['results'].values()),
                    'missing or unusable result requires a terminated attempt without a timely result')
            a['no_result'] = proof
        else:
            require(a['execution'] == 'terminated' and a['effects'] == 'unreconciled' and
                    p.get('disposition') in ('clean', 'isolated', 'integrated'), 'reconcile effects after observed termination')
            a['effects'] = p['disposition']
        a.setdefault('observations', []).append({'action': action, 'evidence': proof, 'at': now})
    elif action == 'result':
        a = find(db, 'attempts', p.get('attempt_id'))
        b = find(db, 'briefs', a['revision_id'])
        require(a['run_id'] and p.get('assignment_id') == a['assignment_id'] and p.get('revision_id') == b['id'],
                'unbound or mismatched result IDs')
        require(p.get('status') in ('SUCCESS', 'PARTIAL', 'BLOCKED') and
                isinstance(p.get('source_versions'), dict) and 'deliverable' in p and
                texts(p.get('evidence_refs')) and texts(p.get('gaps')), 'malformed result')
        if b['mode'] != 'read':
            require(isinstance(p.get('affected_paths'), dict) and texts(p.get('deviations')) and
                    texts(p.get('follow_ups')) and isinstance(p.get('verification'), dict) and
                    set(p['verification']) == set(b['commands']) and
                    all(isinstance(v, dict) and ((text(v.get('output')) and type(v.get('exit_code')) is int and
                            not v.get('not_run')) or (text(v.get('not_run')) and not v.get('output') and 'exit_code' not in v))
                        for v in p['verification'].values()), 'missing authorized verification or workspace result fields')
        late = bool(a['no_result'] or active_brief(db, b['assignment_id']) != b or
                    any(x['assignment_id'] == a['assignment_id'] and x['recorded_at'] > a['recorded_at']
                        for x in db['attempts'].values()))
        require(late or not any(r['attempt_id'] == a['id'] and not r['late'] for r in db['results'].values()),
                'attempt already has a timely result')
        add(db, 'results', key, {**p, 'late': late}, now)
    elif action == 'decision':
        a = find(db, 'attempts', p.get('attempt_id'))
        b = find(db, 'briefs', a['revision_id'])
        require(text(p.get('rationale')) and p.get('verdict') in ('accepted', 'rejected'), 'invalid Lead decision')
        prior = p.get('supersedes')
        if prior:
            old = find(db, 'decisions', prior)
            require(current_decision(db, prior) and find(db, 'briefs', old['revision_id'])['assignment_id'] == b['assignment_id'],
                    'supersession must target a current decision for this assignment')
        require(not any(d['attempt_id'] == a['id'] and current_decision(db, d['id']) and d['id'] != prior
                        for d in db['decisions'].values()), 'supersede the existing attempt decision explicitly')
        if p['verdict'] == 'accepted':
            r = find(db, 'results', p.get('result_id'))
            require(a['execution'] == 'terminated' and not a['cutoff'] and not r['late'] and
                    r['attempt_id'] == a['id'] and r['status'] == 'SUCCESS' and r['evidence_refs'] and
                    r['deliverable'] and r['source_versions'] == b['source_versions'] and
                    active_brief(db, b['assignment_id']) == b and b['id'] not in invalid_consumers(db),
                    'acceptance requires a verified, timely SUCCESS against active pinned inputs')
            check_consumer(db, b['id'], root)
            require(all(v.get('exit_code') == 0 for v in r.get('verification', {}).values()),
                    'required verification failed or was not run')
        elif p.get('result_id'):
            require(find(db, 'results', p['result_id'])['attempt_id'] == a['id'], 'result belongs to a different attempt')
        add(db, 'decisions', key, {**p, 'revision_id': b['id']}, now)
    elif action == 'record-availability':
        d = find(db, 'decisions', p.get('decision_id'))
        a = find(db, 'attempts', d['attempt_id'])
        b = find(db, 'briefs', d['revision_id'])
        require(d['verdict'] == 'accepted' and current_decision(db, d['id']) and b['id'] not in invalid_consumers(db)
                and not any(x['decision_id'] == d['id'] for x in db['availability'].values()), 'needs current unintegrated acceptance')
        require(not attempt_open(a), 'reconcile execution effects first')
        verify_artifacts(root, p.get('artifacts'))
        if b['mode'] == 'write':
            require(text(p.get('checkpoint')) and a['effects'] == 'integrated', 'accepted write needs verified integration')
            require(GIT_HASH.fullmatch(p['checkpoint']), 'use a full Git checkpoint hash')
            for base, tip in ((p['checkpoint'], 'HEAD'), (b['base_revision'], p['checkpoint'])):
                require(GIT_HASH.fullmatch(base), 'use a full Git base hash')
                g = subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', base, tip],
                                   capture_output=True, timeout=10)
                require(g.returncode == 0, 'checkpoint must integrate the recorded base into project history')
            repo = subprocess.run(['git', '-C', str(root), 'rev-parse', '--show-prefix'],
                                  capture_output=True, text=True, timeout=10)
            require(repo.returncode == 0, 'unable to resolve project Git-relative location')
            prefix = repo.stdout.rstrip('\n')
            for name, digest_ in p['artifacts'].items():
                blob = subprocess.run(['git', '-C', str(root), 'show', f"{p['checkpoint']}:{prefix}{name}"],
                                      capture_output=True, timeout=10)
                require(blob.returncode == 0 and hashlib.sha256(blob.stdout).hexdigest() == digest_,
                        f'accepted bytes missing from exact Git checkpoint: {name}')
        add(db, 'availability', key, p, now)
    elif action == 'pin-use':
        d = find(db, 'decisions', p.get('decision_id'))
        require(usable(db, d) and ident(p.get('consumer')) and type(p.get('required')) is bool,
                'pin exact available acceptance and consumer')
        require(p['consumer'] != d['revision_id'], 'cannot consume own acceptance')
        pending, visited = [d['revision_id']], set()
        while pending:
            consumer = pending.pop()
            require(consumer != p['consumer'], 'circular evidence use')
            if consumer not in visited:
                visited.add(consumer)
                pending.extend(db['decisions'][u['decision_id']]['revision_id'] for u in db['uses'].values()
                               if u['consumer'] == consumer)
        available = next(x for x in db['availability'].values() if x['decision_id'] == d['id'])
        require(p.get('output') in available['artifacts'], 'output is not part of the available evidence')
        verify_artifacts(root, {p['output']: available['artifacts'][p['output']]})
        add(db, 'uses', key, p, now)
    elif action == 'drop-optional':
        b = find(db, 'briefs', p.get('revision_id'))
        require(p.get('optional') is True and active_brief(db, b['assignment_id']) == b and text(p.get('gap')) and
                not any(a['assignment_id'] == b['assignment_id'] and attempt_open(a) for a in db['attempts'].values()),
                'drop needs current optional work, recorded gap and settled attempts')
        require(not any(d['revision_id'] == b['id'] and current_decision(db, d['id']) and d['verdict'] == 'accepted'
                        for d in db['decisions'].values()), 'cannot drop currently accepted work')
        add(db, 'drops', key, {**p, 'beads_task_id': b['beads_task_id']}, now)
    else:
        raise ValueError(f'unknown evidence operation: {action}')
    return {'record_id': key, 'launch_eligible': action == 'reserve'}


def get(state, key):
    db = state['execution']
    for k in KINDS:
        if key in db[k]:
            return {'kind': k, 'record': copy.deepcopy(db[k][key])}
    rows = [x for x in db['briefs'].values() if x['assignment_id'] == key]
    require(rows, f'unknown evidence ID: {key!r}')
    return {'kind': 'assignment', 'id': key, 'revision_ids': [x['id'] for x in rows],
            'active_revision_id': active_brief(db, key)['id']}
