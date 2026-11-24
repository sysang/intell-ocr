"""Mechanics for phase-aware Advisor reviews; the Lead chooses the route."""
import re

from evidence import check_consumer, digest, ident, require, text, texts, verify_artifacts

PHASES = {'PLAN_GATE': ('protocol', 'readiness'), 'INNER_EXIT_GATE': ('complete', 'diagnosis'),
          'CYCLE_GATE': ('cycle',), 'REPORT_GATE': ('report',)}
STAGE = {'protocol': {'PLANNING'}, 'readiness': {'IMPLEMENTING'},
         'complete': {'EVALUATING'}, 'diagnosis': {'IMPLEMENTING', 'EVALUATING'},
         'cycle': {'ANALYZING'}, 'report': {'REPORTING'}}


def validate_verdict(verdict, gate, manifest_id):
    require(isinstance(verdict, dict) and verdict.get('gate') == gate and
            verdict.get('review_target') == manifest_id, 'verdict gate/target does not match submission')
    require(verdict.get('verdict') in ('approve', 'revise', 'block', 'inconclusive') and text(verdict.get('summary')),
            'invalid verdict or summary')
    for field in ('alternative_explanations', 'residual_uncertainties', 'recommended_next_actions',
                  'additional_evidence_required'):
        require(texts(verdict.get(field)), f'invalid {field}')
    findings = verdict.get('findings')
    require(isinstance(findings, list) and all(isinstance(x, dict) and
            x.get('severity') in ('critical', 'major', 'minor') and
            all(text(x.get(k)) for k in ('issue', 'justification', 'required_action')) and
            texts(x.get('evidence_refs')) for x in findings), 'invalid findings')
    require(verdict['verdict'] not in ('revise', 'block') or findings, 'required correction is missing')
    require(verdict['verdict'] != 'inconclusive' or verdict['additional_evidence_required'], 'missing evidence not named')
    return verdict['verdict']


def check_manifest(manifest, gate, phase, root):
    require(isinstance(manifest, dict) and phase in PHASES.get(gate, ()) and
            manifest.get('gate') == gate and manifest.get('phase') == phase and text(manifest.get('id')) and
            re.fullmatch(r'[A-Za-z0-9_.:-]+@[A-Za-z0-9_.:-]+', manifest['id']), 'manifest must name exact gate, phase, and id@version')
    verify_artifacts(root, manifest.get('artifacts'))


def predicates(state):
    cycle = state['lifecycle']['outer_cycle']
    budgets = state['budgets']['outer_cycles']
    progress = {p['cycle']: p for p in state['progress_verdicts']}
    n = state['policy']['stagnation_cycles']
    tail = [progress.get(i, {}) for i in range(cycle - n + 1, cycle + 1)]
    return {'objective_achieved': bool(state['objectives']) and all(o['status'] == 'met' for o in state['objectives']),
            'confirmed_blocker': any(b['status'] == 'confirmed-unresolvable' for b in state['blockers']),
            'cycle_cap': budgets['used'] >= budgets['max'],
            'early_stagnation': all(p.get('verdict') in ('stalled', 'regressed') and
                                    p.get('credible_lever') is False for p in tail)}


def review_basis(state, phase):
    if phase == 'cycle':
        return digest([state['objectives'], state['progress_verdicts'], state['lifecycle']['plan_version']])
    return None


def latest_approval(state, phase, root):
    cycle = state['lifecycle']['outer_cycle']
    rows = [(key, r) for key, r in state['gate_reviews'].items() if r['cycle'] == cycle and r['phase'] == phase]
    require(rows, f'no {phase} review for current cycle')
    key, r = rows[-1]
    require(r['verdict'] == 'approve' and r['route'] == 'continue', f'{phase} approval unavailable')
    check_consumer(state['execution'], key, root)
    check_manifest(r['manifest'], r['gate'], phase, root)


def advance(state, action, p, now, root):
    lc, db, cycle = state['lifecycle'], state['gate_reviews'], state['lifecycle']['outer_cycle']
    result = {'launch_eligible': False}
    require(lc['status'] != 'suspended' and lc['stage'] != 'COMPLETED', 'project is terminal')
    if action == 'resolve-hold':
        require(lc['status'] == 'hold' and text(p.get('resolution')), 'HOLD resolution required')
        require(not any(x['status'] == 'confirmed-unresolvable' for x in state['blockers']), 'confirmed blocker remains')
        lc.update(status='active', hold_reason=None)
        return result
    if action == 'suspend-held':
        require(lc['status'] == 'hold' and text(p.get('status_report')) and
                (predicates(state)['confirmed_blocker'] or text(p.get('director_decision'))),
                'need status report and confirmed blocker or director decision')
        lc['status'] = 'suspended'
        lc['status_report'] = p['status_report']
        return result
    require(lc['status'] == 'active' or action == 'record-blocker', 'project is on HOLD')
    if action == 'open-hold':
        require(text(p.get('reason')), 'record a HOLD reason')
        lc.update(status='hold', hold_reason=p['reason'])
    elif action == 'start-scoping':
        require(lc['stage'] == 'CREATED', 'expected CREATED')
        lc['stage'] = 'SCOPING'
    elif action == 'start-planning':
        require(lc['stage'] == 'SCOPING' and text(p.get('charter_ref')), 'expected SCOPING with charter')
        state['identity']['charter_ref'] = p['charter_ref']
        lc['stage'] = 'PLANNING'
    elif action == 'record-blocker':
        key = p.get('id')
        require(ident(key) and text(p.get('description')) and
                p.get('status') in ('open', 'confirmed-unresolvable', 'resolved'),
                'blocker ID, description, and status required')
        state['blockers'] = [b for b in state['blockers'] if b['id'] != key]
        state['blockers'].append({'id': key, 'description': p['description'], 'status': p['status'], 'since': now})
        if p['status'] == 'confirmed-unresolvable':
            lc.update(status='hold', hold_reason=f'confirmed blocker: {key}')
    elif action == 'begin-inner-attempt':
        require(lc['stage'] == 'IMPLEMENTING' and lc['inner_attempt'] < state['policy']['inner_limit'],
                'in-plan implementation with remaining inner attempts required')
        latest_approval(state, 'protocol', root)
        lc['inner_attempt'] += 1
    elif action == 'record-consultation':
        require(ident(p.get('id')) and not any(c['id'] == p['id'] for c in state['consultations']) and
                p.get('agent') in ('research-advisor', 'harness-architector', 'frontend-architector', 'backend-architector') and
                p.get('status') in ('completed', 'no-verdict', 'timeout', 'error') and text(p.get('evidence_ref')) and
                (ident(p.get('run_id')) or (p['status'] != 'completed' and p.get('run_id') is None)),
                'invalid consultation observation')
        state['consultations'].append({**p, 'kind': 'advice', 'recorded_at': now})
    elif action == 'objective':
        matches = [o for o in state['objectives'] if o['id'] == p.get('id')]
        require(matches and p.get('status') in ('untested', 'partial', 'met', 'failed') and
                texts(p.get('evidence_refs')) and (p['status'] != 'met' or p['evidence_refs']), 'invalid objective update')
        matches[0].update(status=p['status'], evidence_refs=p['evidence_refs'])
    elif action == 'progress':
        require(lc['stage'] == 'ANALYZING' and p.get('verdict') in ('advanced', 'marginal', 'stalled', 'regressed') and
                type(p.get('credible_lever')) is bool and texts(p.get('evidence_refs')) and p['evidence_refs'], 'invalid progress assessment')
        state['progress_verdicts'] = [x for x in state['progress_verdicts'] if x['cycle'] != cycle]
        state['progress_verdicts'].append({'cycle': cycle, **{k: p[k] for k in ('verdict', 'credible_lever', 'evidence_refs')}})
    elif action == 'gate-review':
        key, gate, phase, run, manifest = (p.get(k) for k in ('id', 'gate', 'phase', 'advisor_run_id', 'manifest'))
        require(ident(key) and key not in db and phase in PHASES.get(gate, ()) and lc['stage'] in STAGE[phase],
                'invalid review ID or gate/phase for current stage')
        if phase == 'readiness':
            latest_approval(state, 'protocol', root)
        if phase == 'complete':
            latest_approval(state, 'readiness', root)
        require(not any(x['cycle'] == cycle and x['gate'] == gate and x['phase'] == phase and x['route'] is None
                        for x in db.values()), 'route the prior recorded review first')
        attempts = [x for x in db.values() if x['cycle'] == cycle and x['phase'] == phase]
        consecutive_failures = 0
        for review in reversed(attempts):
            if review['verdict'] != 'none': break
            consecutive_failures += 1
        require(consecutive_failures < 3, 'no-verdict re-requests exhausted; escalate')
        verdict = 'none'
        issue = p.get('failure')
        try:
            require(not issue, 'Advisor run did not yield a usable verdict')
            check_manifest(manifest, gate, phase, root)
            require(not any(isinstance(x['manifest'], dict) and x['manifest'].get('id') == manifest['id'] and
                            x['manifest'] != manifest for x in db.values()), 'manifest ID reused with different contents')
            require(ident(run) and not any(r.get('advisor_run_id') == run for r in db.values()),
                    'unique exact Advisor run ID required')
            check_consumer(state['execution'], key, root)
            verdict = validate_verdict(p.get('verdict'), gate, manifest['id'])
            issue = None
        except (ValueError, OSError) as exc:
            require(text(issue) or p.get('verdict') is not None, 'record a failure reason when no verdict was returned')
            issue = issue or str(exc)
        db[key] = {'cycle': cycle, 'gate': gate, 'phase': phase, 'manifest': manifest, 'verdict': verdict,
                   'output': p.get('verdict'), 'advisor_run_id': run, 'failure': issue, 'route': None, 'at': now,
                   'basis': review_basis(state, phase)}
        if verdict in ('none', 'block'):
            lc.update(status='hold', hold_reason=f'{gate}/{phase}: {issue or verdict}')
            db[key]['route'] = 'hold'
        result['record_id'] = key
        result['verdict'] = verdict
    elif action == 'withdraw-stale-review':
        key = p.get('id')
        r = db.get(key)
        require(r and r['cycle'] == cycle and not r['route'], 'only a current unrouted review may be withdrawn')
        require(any(f['review_id'] == key for f in flags(state, root, include_nonapproval=True)),
                'review still covers its manifest; choose its legal route')
        r['route'] = 'withdrawn-stale'
    elif action == 'gate-route':
        key, route = p.get('id'), p.get('route')
        r = db.get(key)
        require(r and r['cycle'] == cycle and r['route'] is None and lc['stage'] in STAGE[r['phase']],
                'fresh unrouted review for current cycle and stage required')
        phase, gate, v = r['phase'], r['gate'], r['verdict']
        check_manifest(r['manifest'], gate, phase, root)
        require(r.get('basis') == review_basis(state, phase), 'gate input state changed; re-review the submission')
        if phase in ('readiness', 'complete'):
            latest_approval(state, 'protocol' if phase == 'readiness' else 'readiness', root)
        check_consumer(state['execution'], key, root)
        previous = [x for x in db.values() if x['cycle'] == cycle and x['phase'] == phase and x['route']]
        pred = predicates(state)
        stopped = pred['cycle_cap'] or pred['early_stagnation']
        plan = r['manifest'].get('next_plan')
        if v == 'inconclusive':
            if any(x['route'] == 'gather-evidence' for x in previous):
                require(route == 'hold', 'evidence recovery exhausted')
            else:
                require(route in ('gather-evidence', 'hold'), 'invalid inconclusive route')
        elif v == 'revise':
            exhausted = sum(x['route'] in ('remediate-plan', 'remediate-implementation', 'remediate-report')
                            for x in previous) >= 2
            allowed = {'hold'}
            if not exhausted:
                if phase == 'protocol': allowed.add('remediate-plan')
                elif phase == 'report': allowed.add('remediate-report')
                else:
                    if phase == 'cycle':
                        allowed.add('stop' if stopped else 'remediate-plan')
                    if lc['inner_attempt'] < state['policy']['inner_limit']:
                        allowed.add('remediate-implementation')
            require(route in allowed, 'invalid revise route or rounds exhausted')
        elif v == 'approve':
            if phase in ('protocol', 'readiness', 'complete'):
                require(route == 'continue', 'approval requires continue')
            elif phase == 'diagnosis':
                require(route == 'continue-to-diagnose', 'diagnosis-only review cannot authorize success claims')
            elif phase == 'report':
                require(route == 'complete', 'expected complete')
            elif phase == 'cycle':
                if pred['objective_achieved'] and not lc.get('diagnosis_only'):
                    require(route == 'report', 'validated achievement takes report before cap')
                elif stopped:
                    require(route == 'stop', 'cycle cap or stagnation forbids replan')
                elif route == 'replan':
                    require(text(plan) and plan != lc['plan_version'] and text(r['manifest'].get('replan_rationale')) and
                            r['manifest'].get('proposed_route') == 'replan', 'no matching reviewed replan proposal')
                else:
                    require(route == 'hold', 'no authorized forward route')
        else:
            raise ValueError('no valid verdict')
        if route == 'hold':
            require(text(p.get('reason')), 'HOLD reason required')
            lc.update(status='hold', hold_reason=p['reason'])
        elif route == 'stop':
            require(text(p.get('status_report')), 'terminal stop requires a status report')
            lc.update(status='suspended', status_report=p['status_report'])
        elif route == 'replan':
            state['budgets']['outer_cycles']['used'] += 1
            lc.update(stage='PLANNING', outer_cycle=cycle + 1, inner_attempt=0, plan_version=plan, diagnosis_only=False)
        elif route == 'continue':
            lc['stage'] = {'protocol': 'IMPLEMENTING', 'readiness': 'EVALUATING', 'complete': 'ANALYZING'}[phase]
            if phase == 'complete': lc['diagnosis_only'] = False
        elif route == 'continue-to-diagnose':
            lc.update(stage='ANALYZING', diagnosis_only=True)
        elif route == 'report': lc['stage'] = 'REPORTING'
        elif route == 'complete': lc['stage'] = 'COMPLETED'
        elif route == 'remediate-implementation': lc['stage'] = 'IMPLEMENTING'
        # Draft next plans and evidence gathering never change cycle/stage here.
        r['route'] = route
        result['record_id'] = key
    else:
        raise ValueError(f'unknown lifecycle event: {action}')
    return result


def candidates(state, root):
    lc = state['lifecycle']
    if lc['status'] == 'suspended' or lc['stage'] == 'COMPLETED':
        return []
    if lc['status'] == 'hold':
        return [{'action': 'triage-hold', 'basis': lc.get('hold_reason')}]
    stale = {flag['review_id'] for flag in flags(state, root, include_nonapproval=True)}
    pending = [(key, r) for key, r in state['gate_reviews'].items()
               if r['cycle'] == lc['outer_cycle'] and r['route'] is None]
    if pending:
        return [{'action': 'withdraw-stale-review' if key in stale else 'select-legal-gate-route',
                 'review_id': key, 'basis': f"{r['phase']} {r['verdict']}"} for key, r in pending]
    stages = {'CREATED': ['start-scoping'], 'SCOPING': ['start-planning'], 'PLANNING': ['review-protocol'],
              'IMPLEMENTING': ['review-readiness', 'consider-diagnosis-only-exit'],
              'EVALUATING': ['continue-evaluation-or-review-exit'], 'ANALYZING': ['review-cycle'], 'REPORTING': ['review-report']}
    options = list(stages.get(lc['stage'], []))
    if lc['stage'] == 'IMPLEMENTING' and lc['inner_attempt'] < state['policy']['inner_limit']:
        options.append('begin-inner-attempt')
    return ([{'action': 'check-evidence-freshness', 'review_id': key, 'basis': 'covered evidence changed'}
             for key in sorted(stale)] + [{'action': action, 'basis': 'stage=' + lc['stage']} for action in options])


def flags(state, root, include_nonapproval=False):
    output = []
    for key, r in state['gate_reviews'].items():
        if (r['cycle'] != state['lifecycle']['outer_cycle'] or r['route'] == 'withdrawn-stale' or
                (r['verdict'] != 'approve' and not include_nonapproval)):
            continue
        try:
            check_consumer(state['execution'], key, root)
            require(r['route'] is not None or r.get('basis') == review_basis(state, r['phase']), 'gate input state changed')
            check_manifest(r['manifest'], r['gate'], r['phase'], root)
        except (ValueError, OSError) as exc:
            output.append({'review_id': key, 'reason': str(exc)})
    return output
