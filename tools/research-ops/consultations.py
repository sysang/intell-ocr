"""Advisor call accounting and exploratory reuse; no provider or dispatch integration."""
import json

from evidence import digest, ident, require, text, texts, verify_artifacts
import task_readiness

CONFIGURE = 'configure-consultations'
RESERVE = 'reserve-consultation'
SETTLE = 'settle-consultation'
REUSE = 'reuse-consultation'
CHECK = 'record-advice-check'
LANES = ('mandatory', 'exploratory')
METRICS = ('tokens', 'model_calls', 'seconds')
OUTCOMES = ('finished', 'failed', 'timed-out', 'non-dispatched')


def shape(p, fields):
    require(isinstance(p, dict) and set(p) == set(fields.split()), f'expected exactly these fields: {fields}')


def receipts(state, action):
    return [r for r in state['operations'].values() if r['group'] == 'lifecycle' and r['action'] == action]


def policies(state):
    return max(receipts(state, CONFIGURE), key=lambda r: r['revision'], default=None)


def policy_shape(p):
    shape(p, 'approval mandatory exploratory')
    for lane in LANES:
        limits = p[lane]
        shape(limits, 'calls attempts_per_issue per_call')
        require(type(limits['calls']) is int and limits['calls'] >= (1 if lane == 'mandatory' else 0) and
                type(limits['attempts_per_issue']) is int and limits['attempts_per_issue'] > 0, 'invalid Advisor call limits')
        metric_values(limits['per_call'], lambda x: type(x) is int and x > 0, 'per-call limits must be positive integers')


def metric_values(values, valid, message):
    require(isinstance(values, dict) and set(values) == set(METRICS) and all(valid(x) for x in values.values()), message)


def attempts(state):
    return {r['op_id']: r for r in receipts(state, RESERVE)}


def settlements(state):
    return {r['attempt_id']: r for r in receipts(state, SETTLE)}


def check_approval(p, root):
    verify_artifacts(root, p['approval'])
    require(len(p['approval']) == 1, 'pin one operator approval JSON file')
    record = json.loads((root / next(iter(p['approval']))).read_text(encoding='utf-8'))
    shape(record, 'id operator mandatory exploratory')
    require(ident(record['id']) and text(record['operator']) and all(digest(p[k]) == digest(record[k]) for k in LANES),
            'limits do not match the pinned operator decision')
    return record['id']


def configure(state, p, root):
    policy_shape(p)
    approval_id = check_approval(p, root)
    require(not any(r['approval_id'] == approval_id for r in receipts(state, CONFIGURE)),
            'policy changes need a new operator approval decision')
    require(not (attempts(state).keys() - settlements(state).keys()), 'reconcile outstanding Advisor attempts before changing limits')
    return {'policy': p, 'approval_id': approval_id}


def require_policy(state, root):
    record = policies(state)
    require(record, 'explicit operator-approved Advisor consultation limits are required')
    require(check_approval(record['policy'], root) == record['approval_id'], 'operator approval no longer matches policy')
    return record


def check_assessment(state, key, root, *, exploratory):
    row = task_readiness.lookup(state, key)
    p = row['assessment']
    task = p['beads_task_id']
    require(row['basis'] == task_readiness.basis(state) and task_readiness.latest(state)[task] == row,
            'current task assessment for this stage and plan required')
    verify_artifacts(root, p['artifacts'])
    if exploratory:
        require(not row['advisor_need'] and p['classification'] in ('READY', 'INVESTIGATE'),
                'optional advice cannot cover a mandatory or blocked task')
        task_readiness.prior_followups(state, task, root)
    else:
        require(p['classification'] == 'CONSULT' and row['advisor_need'] == 'advice' and not task_readiness.followup(state, row),
                'an unresolved required Advisor consultation is needed')
    return task


def exploratory_inputs(p, root):
    shape(p, 'question assumptions constraints artifacts')
    require(text(p['question']) and texts(p['assumptions']) and texts(p['constraints']),
            'identify the exact question, assumptions and constraints')
    verify_artifacts(root, p['artifacts'])
    return p


def reserve(state, p, root):
    policy = require_policy(state, root)
    purpose = p.get('purpose')
    required = 'purpose assessment_id pass brief limits'
    require(purpose in ('gate', 'task-advice', 'exploratory'), 'unrecognized Advisor call purpose')
    shape(p, required + {'gate': ' manifest' + (' okf_check' if 'okf_check' in p else ''),
                         'task-advice': '', 'exploratory': ' inputs'}[purpose])
    require(p['pass'] in ('evidence-first', 'decision') and (purpose != 'exploratory' or p['pass'] == 'decision'),
            'invalid consultation pass for this purpose')
    lc = state['lifecycle']
    if purpose == 'gate':
        # The lifecycle checks the stage, assessment, and manifest before reaching this function.
        manifest = p['manifest']
        target = {'gate': manifest['gate'], 'phase': manifest['phase'], 'manifest_sha256': digest(manifest)}
        issue = f"gate:{lc['outer_cycle']}:{manifest['gate']}:{manifest['phase']}"
    else:
        task = check_assessment(state, p['assessment_id'], root, exploratory=purpose == 'exploratory')
        target = {'beads_task_id': task}
        if purpose == 'exploratory':
            target['inputs'] = exploratory_inputs(p['inputs'], root)
        issue = f'task:{task}'
    target['assessment_id'] = p['assessment_id']
    lane = 'exploratory' if purpose == 'exploratory' else 'mandatory'
    verify_artifacts(root, p['brief'])
    limits = policy['policy'][lane]
    metric_values(p['limits'], lambda x: type(x) is int and x > 0, 'requested call limits must be positive integers')
    require(all(v <= limits['per_call'][k] for k, v in p['limits'].items()), 'requested call exceeds per-call allowance')
    known = settlements(state)
    require(not any(r['over_limit'] and r['revision'] > policy['revision'] for r in known.values()),
            'observed Advisor limit overrun needs operator review and a new approved policy')
    prior = [r for key, r in attempts(state).items() if key not in known or known[key]['outcome'] != 'non-dispatched']
    require(not any(r['issue'] == issue and r['op_id'] not in known for r in prior), 'reconcile the unresolved Advisor attempt for this issue')
    require(sum(r['lane'] == lane for r in prior) < limits['calls'], f'{lane} Advisor call budget exhausted')
    require(sum(r['lane'] == lane and r['issue'] == issue for r in prior) < limits['attempts_per_issue'],
            'Advisor attempt limit for this issue exhausted')
    return {'launch_eligible': True, 'policy_id': policy['op_id'], 'purpose': purpose, 'pass': p['pass'], 'lane': lane,
            'issue': issue, 'target': target, 'basis': task_readiness.basis(state), 'brief': p['brief'], 'limits': p['limits']}


def settle(state, p, root):
    shape(p, 'attempt_id outcome run_id artifacts usage')
    key, outcome, run = p['attempt_id'], p['outcome'], p['run_id']
    known = settlements(state)
    attempt = attempts(state).get(key) if ident(key) else None
    require(attempt and key not in known and outcome in OUTCOMES, 'fresh settlement for an exact Advisor attempt required')
    metric_values(p['usage'], lambda x: x is None or (type(x) is int and x >= 0),
                  'usage needs nonnegative observed counters or explicit nulls')
    if outcome == 'non-dispatched':
        require(run is None and not any(p['usage'].values()), 'releasing a slot needs proof of non-dispatch, not an ended run')
    else:
        require(ident(run) or (run is None and outcome != 'finished'), 'a finished call needs the exact Pi run ID')
    if run:
        require(not any(r['run_id'] == run for r in known.values()) and
                not any(c.get('run_id') == run for c in state['consultations']) and
                not any(r.get('advisor_run_id') == run for r in state['gate_reviews'].values()), 'Advisor run already recorded')
    verify_artifacts(root, p['artifacts'])
    return {**p, 'over_limit': [k for k in METRICS if p['usage'][k] is not None and p['usage'][k] > attempt['limits'][k]]}


def consume(state, p, root, *, gate=False):
    # Unconfigured snapshots retain inspection/fixture compatibility; the enabled launcher requires policy.
    key = p.get('attempt_id')
    if key is None and not policies(state):
        return None
    attempt = attempts(state).get(key) if ident(key) else None
    observation = settlements(state).get(key) if attempt else None
    require(observation and observation['outcome'] != 'non-dispatched', 'record the exact settled Advisor attempt before using output')
    require(not any(c.get('attempt_id') == key for c in state['consultations']) and
            not any(r.get('attempt_id') == key for r in state['gate_reviews'].values()), 'Advisor attempt already consumed')
    target = attempt['target']
    if gate:
        manifest = p.get('manifest')
        require(attempt['purpose'] == 'gate' and attempt['pass'] == 'decision' and
                all(p.get(k) == target[k] for k in ('gate', 'phase', 'assessment_id')) and
                digest(manifest) == target['manifest_sha256'] and p.get('advisor_run_id') == observation['run_id'],
                'gate result must match the reserved manifest, assessment and actual run')
    else:
        eligible = attempt['purpose'] in ('task-advice', 'exploratory') or attempt['pass'] == 'evidence-first'
        expected_assessment = target['assessment_id'] if (attempt['purpose'], attempt['pass']) == ('task-advice', 'decision') else None
        require(eligible and p.get('assessment_id') == expected_assessment and p.get('run_id') == observation['run_id'],
                'advice must match the settled run and consultation purpose')
    verify_artifacts(root, observation['artifacts'])
    usable = (observation['outcome'] == 'finished' and not observation['over_limit'] and
              all(v is not None for v in observation['usage'].values()))
    complete = not p.get('failure') if gate else p['status'] == 'completed'
    if complete and usable:
        verify_artifacts(root, attempt['brief'])
        require(attempt['basis'] == task_readiness.basis(state), 'consultation basis changed; record the result as unusable')
    if not gate:
        require(not complete or usable, 'completed advice needs a finished call with complete in-limit usage evidence')
        if complete:
            require(p.get('disposition') in ('accepted', 'adapted', 'declined') and text(p.get('rationale')),
                    'record the Lead disposition and rationale for completed advice')
            verify_artifacts(root, p.get('artifacts'))
            require(text(p.get('evidence_ref')) and p['evidence_ref'] in p['artifacts'], 'pin the result named by evidence_ref')
        if complete and attempt['purpose'] == 'exploratory':
            verify_artifacts(root, target['inputs']['artifacts'])
    return {'attempt_id': key, 'consultation_lane': attempt['lane'], 'consultation_pass': attempt['pass'], 'usable': usable}


def check_review(state, review, root):
    key = review.get('attempt_id')
    if key:
        attempt = attempts(state).get(key)
        observation = settlements(state).get(key)
        require(attempt and observation, 'missing recorded Advisor attempt or settlement')
        verify_artifacts(root, attempt['brief'])
        verify_artifacts(root, observation['artifacts'])


def advice(state, key):
    record = next((c for c in state['consultations'] if c['id'] == key), None)
    require(record and record['agent'] == 'research-advisor' and record.get('status') == 'completed' and
            record.get('disposition') in ('accepted', 'adapted', 'declined'), 'no completed Advisor advice with a Lead disposition')
    return record


def reuse(state, p, root):
    shape(p, 'consultation_id assessment_id inputs rationale')
    require(text(p['rationale']), 'record why this advice applies')
    task = check_assessment(state, p['assessment_id'], root, exploratory=True)
    source = advice(state, p['consultation_id'])
    attempt = attempts(state).get(source.get('attempt_id'))
    require(attempt and attempt['purpose'] == 'exploratory' and source['disposition'] in ('accepted', 'adapted'),
            'only eligible exploratory advice may be reused; never a mandatory review')
    require(attempt['basis'] == task_readiness.basis(state) and attempt['target']['beads_task_id'] == task and
            attempt['target']['inputs'] == exploratory_inputs(p['inputs'], root),
            'question, evidence, assumptions, constraints, or project context changed')
    require(not any(r['consultation_id'] == source['id'] and r['finding'] == 'contradicted' for r in receipts(state, CHECK)),
            'recorded evidence contradicts this advice')
    verify_artifacts(root, source['artifacts'])
    verify_artifacts(root, attempt['brief'])
    original = task_readiness.lookup(state, attempt['target']['assessment_id'])
    verify_artifacts(root, original['assessment']['artifacts'])
    verify_artifacts(root, settlements(state)[attempt['op_id']]['artifacts'])
    return {**p, 'source_attempt': attempt['op_id']}


def record_check(state, p, root):
    shape(p, 'consultation_id finding rationale artifacts')
    source = advice(state, p['consultation_id'])
    require(p['finding'] in ('supported', 'contradicted', 'inconclusive') and text(p['rationale']), 'record the observed check and caveats')
    verify_artifacts(root, source['artifacts'])
    verify_artifacts(root, p['artifacts'])
    require(p['artifacts'].keys().isdisjoint(source['artifacts']), 'link independent observations, not the advice itself')
    return p


def validate(state):
    for record in receipts(state, CONFIGURE):
        policy_shape(record['policy'])
        require(ident(record['approval_id']) and isinstance(record['policy']['approval'], dict) and len(record['policy']['approval']) == 1,
                'invalid Advisor policy approval reference')
    for key, attempt in attempts(state).items():
        policy = state['operations'][attempt['policy_id']]
        require(policy['action'] == CONFIGURE and policy['group'] == 'lifecycle' and policy['revision'] < attempt['revision'] and
                attempt['lane'] in LANES and ident(key), 'invalid Advisor attempt binding')
    known = receipts(state, SETTLE)
    require(len(known) == len(settlements(state)), 'duplicate Advisor settlement')
    by_id = attempts(state)
    for record in known:
        require(by_id[record['attempt_id']]['revision'] < record['revision'] and record['outcome'] in OUTCOMES,
                'invalid Advisor settlement binding')
        metric_values(record['usage'], lambda x: x is None or (type(x) is int and x >= 0), 'invalid observed Advisor usage')


def view(state):
    policy, known, all_attempts = policies(state), settlements(state), attempts(state)
    if not policy:
        return {'configured': False}
    lanes = {}
    for lane in LANES:
        rows = {key: r for key, r in all_attempts.items() if r['lane'] == lane and
                (key not in known or known[key]['outcome'] != 'non-dispatched')}
        maximum = policy['policy'][lane]['calls']
        lanes[lane] = {'max_calls': maximum, 'charged': len(rows), 'remaining': max(0, maximum - len(rows)),
                       'observed_usage': {m: sum(known[k]['usage'][m] for k in rows if k in known and known[k]['usage'][m] is not None)
                                          for m in METRICS},
                       'missing_usage': {m: sum(k not in known or known[k]['usage'][m] is None for k in rows) for m in METRICS}}
    return {'configured': True, 'policy_id': policy['op_id'], 'lanes': lanes,
            'outstanding': [k for k in all_attempts if k not in known],
            'overruns_pending_review': [k for k, r in known.items() if r['over_limit'] and r['revision'] > policy['revision']]}
