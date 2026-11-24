"""Serialization, guarded operations, and atomic publication of project state."""
import copy
import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

import consultations
import evidence
import gates
import hub_publication
import snapshot_schema
import task_readiness


@contextmanager
def lock(path):
    # Keep the lock inode stable while project-state.json is atomically replaced.
    with open(path.with_suffix('.lock'), 'a', encoding='utf-8') as guard:
        fcntl.flock(guard, fcntl.LOCK_EX)
        yield


def save(path, value):
    fd, tmp = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(value, f, indent=2, allow_nan=False)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(tmp).unlink(missing_ok=True)


def new_state(project_id, objectives, outer, inner, charter, stagnation):
    evidence.require(evidence.ident(project_id) and evidence.texts(objectives) and objectives and
                     3 <= outer <= 5 and inner > 0 and stagnation >= 2, 'invalid project initialization')
    state = {'format': 1, 'revision': 0, 'operations': {}, 'execution': evidence.empty(), 'gate_reviews': {},
            'policy': {'inner_limit': inner, 'stagnation_cycles': stagnation},
            'identity': {'project_id': project_id, 'charter_ref': charter, 'protocol_version': '1'},
            'lifecycle': {'stage': 'CREATED', 'status': 'active', 'outer_cycle': 1, 'inner_attempt': 0, 'plan_version': 'v1'},
            'budgets': {'outer_cycles': {'max': outer, 'used': 0}},
            'objectives': [{'id': f'O-{i}', 'text': o, 'status': 'untested', 'evidence_refs': []}
                           for i, o in enumerate(objectives, 1)],
            'assignments': [], 'progress_verdicts': [], 'gates': {}, 'blockers': [], 'consultations': [], 'decisions': []}
    problems = validate(state)
    evidence.require(not problems, '; '.join(problems))
    return state


def validate(state):
    if problems := snapshot_schema.violations(state):
        return problems
    try:
        evidence.require(type(state['format']) is int and state['format'] == 1 and
                         type(state['revision']) is int and state['revision'] >= 0 and
                         not state['assignments'], 'unsupported format or legacy assignment records present')
        ops = state['operations']
        evidence.require(all(key == row['op_id'] for key, row in ops.items()) and len(ops) == state['revision'] and
                         all(r['revision'] == i for i, r in enumerate(sorted(ops.values(), key=lambda r: r['revision']), 1)),
                         'missing or invalid operation receipts')
        evidence.require(all(type(state['policy'][k]) is int and state['policy'][k] >= lower
                             for k, lower in (('inner_limit', 1), ('stagnation_cycles', 2))), 'invalid policy limits')
        lc = state['lifecycle']
        budget, cycle = state['budgets']['outer_cycles'], lc['outer_cycle']
        used = budget['used']
        evidence.require(used <= budget['max'], 'used cycles exceed the charter limit')
        evidence.require(lc['inner_attempt'] <= state['policy']['inner_limit'], 'used inner attempts exceed the policy limit')
        evidence.require(lc['status'] != 'suspended' or lc['stage'] == 'COMPLETED' or evidence.text(lc.get('status_report')),
                         'SUSPENDED with no status report')
        evidence.require(all(o['status'] != 'met' or o['evidence_refs'] for o in state['objectives']),
                         'objective marked met with no evidence_refs')
        # Pre-planning snapshots from the old initializer already show cycle 1 charged.
        before_planning = lc['stage'] in ('CREATED', 'SCOPING')
        evidence.require(type(used) is int and type(cycle) is int and
                         (cycle == 1 and used in (0, 1) if before_planning else cycle >= 1 and used == cycle),
                         'cycle charge mismatch')
        if 'pending_inner_attempt' in lc:
            pending = lc['pending_inner_attempt']
            base = pending['base_revision']
            start = state['operations'][pending['start_op_id']]
            evidence.require(lc['stage'] == 'IMPLEMENTING' and set(pending) == {'start_op_id', 'base_revision'} and
                             evidence.GIT_HASH.fullmatch(base) and start['group'] == 'lifecycle' and
                             start['action'] == 'begin-inner-attempt' and start['cycle'] == cycle and
                             start['base_revision'] == base and start['start_op_id'] == pending['start_op_id'],
                             'invalid pending inner attempt binding')
        for review in state['gate_reviews'].values():
            evidence.require(review['phase'] in gates.PHASES[review['gate']] and review['cycle'] <= cycle,
                             'invalid gate review phase or cycle')
            if review['verdict'] != 'none':
                evidence.require(all(review[field] == review['manifest'][field] for field in ('gate', 'phase')),
                                 'gate review manifest binding mismatch')
        task_readiness.validate(state)
        consultations.validate(state)
        hub_publication.operation_state(state)
        db = state['execution']
        evidence.require(set(db) == set(evidence.KINDS) and all(isinstance(rows, dict) for rows in db.values()), 'invalid evidence tables')
        ids = set()
        for rows in db.values():
            for key, item in rows.items():
                evidence.require(evidence.ident(key) and key == item['id'] and key not in ids, 'duplicate or malformed evidence ID')
                ids.add(key)
        for attempt in db['attempts'].values():
            brief = evidence.find(db, 'briefs', attempt['revision_id'])
            evidence.require(attempt['assignment_id'] == brief['assignment_id'] and attempt['execution'] in
                             ('dispatch_pending', 'launch_unknown', 'dispatched', 'terminated', 'not_dispatched'),
                             'invalid attempt binding')
        runs = [a['run_id'] for a in db['attempts'].values() if a['run_id']]
        evidence.require(len(runs) == len(set(runs)), 'duplicate Pi run binding')
        for result in db['results'].values():
            attempt = evidence.find(db, 'attempts', result['attempt_id'])
            evidence.require(all(result[k] == attempt[k] for k in ('assignment_id', 'revision_id')), 'result binding mismatch')
        for d in db['decisions'].values():
            attempt = evidence.find(db, 'attempts', d['attempt_id'])
            evidence.require(d['revision_id'] == attempt['revision_id'], 'decision binding mismatch')
            if d.get('result_id'):
                evidence.require(evidence.find(db, 'results', d['result_id'])['attempt_id'] == attempt['id'], 'result mismatch')
            if d.get('supersedes'):
                evidence.find(db, 'decisions', d['supersedes'])
        for kind in ('availability', 'uses'):
            for row in db[kind].values():
                evidence.find(db, 'decisions', row['decision_id'])
        return []
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        return [f'invalid managed state: {exc}']


def apply(state, group, action, payload, op_id, expected, actor, reason, now, root):
    evidence.require(state.get('format') == 1, 'legacy snapshot: migrate explicitly before using managed operations')
    evidence.require(evidence.ident(op_id) and evidence.text(actor) and evidence.text(reason) and
                     type(expected) is int and expected >= 0 and isinstance(payload, dict), 'operation metadata required')
    fingerprint = evidence.digest([group, action, payload, expected, actor, reason])
    old = state['operations'].get(op_id)
    if old:
        evidence.require(old['fingerprint'] == fingerprint, 'operation ID reused with different input')
        return None, {**old, 'replayed': True, 'launch_eligible': False}
    evidence.require(expected == state['revision'], f"revision conflict; current={state['revision']}")
    new = copy.deepcopy(state)
    if group == 'evidence':
        if action == task_readiness.ACTION:
            receipt = {'launch_eligible': False, **task_readiness.assess(new, payload, root)}
            if receipt['advisor_need'] == 'gate':
                gates.check_task_target(new, payload['gate'])
        else:
            if action in ('issue', 'mark-ready', 'reserve'):
                brief = (payload if action == 'issue' else evidence.find(new['execution'], 'briefs',
                         payload.get('id' if action == 'mark-ready' else 'revision_id')))
                task_readiness.check_assignment(new, brief, root)
            receipt = evidence.transition(new, action, payload, now, root)
    else:
        if action == 'record-consultation' and 'assessment_id' in payload:
            task_readiness.check_advice(new, payload, root)
        receipt = gates.advance(new, action, payload, now, root, op_id=op_id)
    new['revision'] += 1
    receipt.update(revision=new['revision'], op_id=op_id, fingerprint=fingerprint,
                   group=group, action=action, actor=actor, reason=reason, at=now, replayed=False)
    # A saved receipt is historical; only this immediate, fresh call can authorize submission.
    new['operations'][op_id] = {**receipt, 'launch_eligible': False}
    problems = validate(new)
    evidence.require(not problems, '; '.join(problems))
    return new, receipt
