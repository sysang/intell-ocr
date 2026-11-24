"""Evidence and routing for meaningful Lead tasks; no backlog or dispatcher."""
import re

from evidence import FIXED, TASK_ID, ident, require, text, texts, verify_artifacts

ACTION = 'assess-task'
DIMENSIONS = ('problem', 'information', 'methodology', 'competence', 'verification', 'risk', 'uncertainty')
UNCERTAINTIES = {'factual', 'conceptual', 'methodological', 'technical', 'interpretive', 'strategic', 'resource'}
TRIGGERS = {'unclear-question', 'unjustified-assumptions', 'material-method-choices', 'no-credible-evaluation',
            'contradictory-evidence', 'hypothesis-undermined', 'repeated-conceptual-failure', 'substantial-interpretation',
            'invalidating-scope-change', 'stage-review-gate'}
CLASSES = ('READY', 'INVESTIGATE', 'CONSULT', 'BLOCKED')


def basis(state):
    lc = state['lifecycle']
    return {k: lc[k] for k in ('stage', 'outer_cycle', 'plan_version')}


def rows(state):
    return sorted((r for r in state['operations'].values()
                   if r['group'] == 'evidence' and r['action'] == ACTION), key=lambda r: r['revision'])


def lookup(state, key):
    row = state['operations'].get(key) if ident(key) else None
    require(row and row['group'] == 'evidence' and row['action'] == ACTION, 'exact task assessment required')
    return row


def latest(state):
    return {r['assessment']['beads_task_id']: r for r in rows(state)}


def matching_advice(state, key):
    return [c for c in state['consultations'] if c.get('assessment_id') == key and c['kind'] == 'advice' and
            c['agent'] == 'research-advisor' and c['status'] == 'completed']


def followup(state, row):
    key = row['op_id']
    if row['advisor_need'] == 'advice':
        matches = matching_advice(state, key)
        if matches:
            return {'consultation_id': matches[-1]['id'], 'artifacts': matches[-1]['artifacts']}
    elif row['advisor_need'] == 'gate':
        for review_id, review in state['gate_reviews'].items():
            if review.get('assessment_id') and review['verdict'] == 'approve' and review['route'] not in (
                    None, 'hold', 'withdrawn-stale'):
                target = lookup(state, review['assessment_id'])
                if (target['revision'] >= row['revision'] and target['basis'] == row['basis'] and
                        all(target['assessment'][k] == row['assessment'][k] for k in ('beads_task_id', 'gate'))):
                    return {'review_id': review_id}
    return None


def prior_followups(state, task_id, root):
    resolved = {}
    for row in rows(state):
        if row['advisor_need'] and row['assessment']['beads_task_id'] == task_id:
            proof = followup(state, row)
            require(proof, f"mandatory Advisor follow-up unresolved for {row['op_id']}")
            if 'artifacts' in proof:
                verify_artifacts(root, proof['artifacts'])
            resolved[row['op_id']] = proof.get('consultation_id', proof.get('review_id'))
    return resolved


def check_route(route):
    require(isinstance(route, dict) and set(route) == {'kind', 'fixed_role', 'handoff', 'required', 'assignee', 'reason'}
            and text(route['reason']) and type(route['required']) is bool, 'provide a reasoned fixed-roster assessment and route')
    kind, role, handoff, required, assignee = (route[k] for k in ('kind', 'fixed_role', 'handoff', 'required', 'assignee'))
    require(role is None or (ident(role) and role in FIXED), 'fixed_role must name a fixed role or be null')
    if kind == 'fixed':
        require(role is not None and assignee == role and handoff == 'eligible', 'route eligible fixed work to its matching role')
    elif kind == 'pool':
        require(role is None and not required and handoff == 'eligible' and ident(assignee) and
                assignee not in FIXED | {'research-lead'}, 'pool requires no matching fixed role (unavailability is not a scope gap)')
    else:
        require(kind == 'lead' and assignee is None and not required and handoff in ('coupled', 'no-eligible-child'),
                'direct work needs a concrete rationale and cannot replace an eligible handoff or a required role')


def check_shape(p):
    required = {'beads_task_id', 'classification', 'dimensions', 'uncertainties', 'triggers', 'artifacts', 'next_step'}
    require(isinstance(p, dict) and required <= p.keys() and not p.keys() - (required | {'routing', 'gate'}),
            'incomplete assessment or unknown fields')
    task, classification = p['beads_task_id'], p['classification']
    require(isinstance(task, str) and TASK_ID.fullmatch(task) and classification in CLASSES and text(p['next_step']),
            'exact Beads task ID, classification, and concrete next step required')
    d = p['dimensions']
    require(isinstance(d, dict) and set(d) == set(DIMENSIONS) and all(text(v) for v in d.values()),
            'provide evidence-based assessments for all seven dimensions')
    uncertainties = p['uncertainties']
    require(isinstance(uncertainties, list) and all(isinstance(u, dict) and
            set(u) == {'kind', 'issue', 'material', 'bounded_check'} and isinstance(u['kind'], str) and
            u['kind'] in UNCERTAINTIES and text(u['issue']) and type(u['material']) is bool and
            (u['bounded_check'] is None or text(u['bounded_check'])) for u in uncertainties),
            'classify uncertainties and give a bounded check when one exists')
    triggers = p['triggers']
    require(texts(triggers) and len(set(triggers)) == len(triggers) and set(triggers) <= TRIGGERS,
            'use the recognized mandatory consultation triggers')
    unbounded = any(u['material'] and u['bounded_check'] is None for u in uncertainties)
    if triggers or unbounded:
        require(classification in ('CONSULT', 'BLOCKED'), 'mandatory Advisor work cannot be bypassed by READY or INVESTIGATE')
    if classification == 'INVESTIGATE':
        require(any(u['bounded_check'] for u in uncertainties), 'INVESTIGATE needs a concrete bounded check')
    if classification == 'READY':
        require(not any(u['material'] for u in uncertainties), 'READY cannot leave material uncertainty unresolved')
        check_route(p.get('routing'))
    else:
        require('routing' not in p, 'only READY records route execution')
    if 'stage-review-gate' in triggers:
        gate = p.get('gate')
        require(isinstance(gate, dict) and set(gate) == {'gate', 'phase'} and text(gate['gate']) and
                text(gate['phase']), 'stage review must name the exact gate and phase')
        return 'gate'
    require('gate' not in p, 'only a required stage review has a gate target')
    return 'advice' if classification == 'CONSULT' or triggers or unbounded else None


def assess(state, p, root):
    lc = state['lifecycle']
    require(lc['stage'] != 'COMPLETED' and (lc['status'] == 'active' or
            (lc['status'] == 'hold' and p.get('classification') == 'BLOCKED')), 'project is not active')
    need = check_shape(p)
    verify_artifacts(root, p['artifacts'])
    resolved = prior_followups(state, p['beads_task_id'], root) if p['classification'] == 'READY' else {}
    return {'assessment': p, 'basis': basis(state), 'advisor_need': need, 'resolved_advisor': resolved}


def check_ready(state, key, root):
    row = lookup(state, key)
    p = row['assessment']
    require(state['lifecycle']['status'] == 'active' and row['basis'] == basis(state) and
            latest(state)[p['beads_task_id']] == row and p['classification'] == 'READY',
            'current READY task assessment for this stage and plan required')
    verify_artifacts(root, p['artifacts'])
    prior_followups(state, p['beads_task_id'], root)
    return p


def check_assignment(state, brief, root):
    p = check_ready(state, brief.get('assessment_id'), root)
    route = p['routing']
    require(p['beads_task_id'] == brief.get('beads_task_id') and route['kind'] in ('fixed', 'pool') and
            route['assignee'] == brief.get('assignee'), 'assignment must match the assessed Beads task and route')
    if route['kind'] == 'pool':
        require(brief.get('routing_reason') == route['reason'], 'pool brief must carry the assessed fixed-roster scope rationale')


def check_advice(state, p, root):
    row = lookup(state, p['assessment_id'])
    require(row['advisor_need'] == 'advice' and p.get('agent') == 'research-advisor',
            'task follow-up needs a non-gate assessment and the Research Advisor')
    if p.get('status') == 'completed':
        require(p.get('disposition') in ('accepted', 'adapted', 'declined') and text(p.get('rationale')),
                'record how the Lead used the advice and why')
        verify_artifacts(root, row['assessment']['artifacts'])
        verify_artifacts(root, p.get('artifacts'))
        require(text(p.get('evidence_ref')) and p['evidence_ref'] in p['artifacts'],
                'pin the actual advice result named by evidence_ref')
        require(not any(c.get('run_id') == p.get('run_id') for c in state['consultations']) and
                not any(r.get('advisor_run_id') == p.get('run_id') for r in state['gate_reviews'].values()),
                'task follow-up requires a distinct Advisor run; cached or gate advice does not qualify')


def check_gate(state, p, root):
    row = lookup(state, p['assessment_id'])
    assessment = row['assessment']
    require(row['advisor_need'] == 'gate' and assessment['classification'] == 'CONSULT' and
            row['basis'] == basis(state) and assessment['gate'] == {k: p.get(k) for k in ('gate', 'phase')} and
            latest(state)[assessment['beads_task_id']] == row and not followup(state, row),
            'gate review must match the current unresolved stage-review assessment')
    verify_artifacts(root, row['assessment']['artifacts'])


def view(state):
    pending = {}
    for row in rows(state):
        if row['advisor_need'] and not followup(state, row):
            pending.setdefault(row['assessment']['beads_task_id'], []).append(row['op_id'])
    return [{'assessment_id': r['op_id'], 'beads_task_id': task,
             'classification': r['assessment']['classification'], 'current_stage_and_plan': r['basis'] == basis(state),
             'pending_advisor': pending.get(task, [])} for task, r in latest(state).items()]


def validate(state):
    for row in rows(state):
        require(check_shape(row['assessment']) == row['advisor_need'] and
                isinstance(row['basis'], dict) and set(row['basis']) == {'stage', 'outer_cycle', 'plan_version'} and
                isinstance(row['resolved_advisor'], dict) and isinstance(row['assessment']['artifacts'], dict) and
                bool(row['assessment']['artifacts']) and all(text(k) and isinstance(v, str) and re.fullmatch('[0-9a-f]{64}', v)
                    for k, v in row['assessment']['artifacts'].items()), 'invalid persisted task assessment')
