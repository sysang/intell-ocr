"""Mechanics for phase-aware Advisor reviews; the Lead chooses the route."""
import re
from subprocess import TimeoutExpired

import consultations
import hub_publication
import inner_attempts
import knowledge
import readiness
import task_readiness
from evidence import check_consumer, digest, ident, require, text, texts, verify_artifacts

PHASES = {'PLAN_GATE': ('protocol', 'readiness'), 'INNER_EXIT_GATE': ('complete', 'diagnosis'),
          'CYCLE_GATE': ('cycle',), 'REPORT_GATE': ('report',)}
STAGE = {'protocol': {'PLANNING'}, 'readiness': {'IMPLEMENTING'},
         'complete': {'EVALUATING'}, 'diagnosis': {'IMPLEMENTING', 'EVALUATING'},
         'cycle': {'ANALYZING'}, 'report': {'REPORTING'}}


def check_task_target(state, target):
    phase = target['phase']
    require(phase in PHASES.get(target['gate'], ()) and state['lifecycle']['stage'] in STAGE[phase],
            'assessment must name a gate phase for the current stage')


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
    require(all(type(manifest.get(key, False)) is bool for key in ('okf_required', 'okf_reader_required')),
            'OKF dependency declarations must be boolean')
    if phase == 'protocol':
        readiness.required_tests(manifest)
    elif phase == 'readiness':
        readiness.check_shape(manifest)


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


def check_readiness(state, manifest, root):
    protocol_key, protocol = latest_approval(state, 'protocol', root)
    return readiness.check_current(state, root, manifest, protocol_key, protocol['manifest'])


def reuse_records(state):
    return (r for r in state['operations'].values() if r['group'] == 'lifecycle' and r['action'] == 'reuse-readiness')


def prior_reuse(state, review):
    return max((r for r in reuse_records(state) if r['review_id'] == review),
               key=lambda r: r['revision'], default=None)


def manifest_identity(state, manifest):
    manifests = [r['manifest'] for r in state['gate_reviews'].values()] + [r['manifest'] for r in reuse_records(state)]
    require(not any(isinstance(m, dict) and m.get('id') == manifest['id'] and m != manifest for m in manifests),
            'manifest ID reused with different contents')


def approved_record(state, phase):
    cycle = state['lifecycle']['outer_cycle']
    rows = [(key, r) for key, r in state['gate_reviews'].items() if r['cycle'] == cycle and r['phase'] == phase]
    require(rows, f'no {phase} review for current cycle')
    key, r = rows[-1]
    require(r['verdict'] == 'approve' and r['route'] == 'continue', f'{phase} approval unavailable')
    return key, r


def latest_approval(state, phase, root):
    key, r = approved_record(state, phase)
    consultations.check_review(state, r, root)
    check_consumer(state['execution'], key, root)
    reuse = prior_reuse(state, key) if phase == 'readiness' else None
    current = reuse['manifest'] if reuse else r['manifest']
    check_manifest(current, r['gate'], phase, root)
    if phase == 'readiness':
        check_readiness(state, current, root)
        if reuse:
            check_consumer(state['execution'], reuse['op_id'], root)
            readiness.check_reuse(state, root, r['manifest'], current, reuse['proof'])
    return key, r


def review_slot(state, gate, phase):
    check_task_target(state, {'gate': gate, 'phase': phase})
    cycle = state['lifecycle']['outer_cycle']
    attempts = [r for r in state['gate_reviews'].values() if r['cycle'] == cycle and r['gate'] == gate and r['phase'] == phase]
    require(all(r['route'] for r in attempts), 'route the prior recorded review first')
    consecutive_failures = 0
    for review in reversed(attempts):
        if review['verdict'] != 'none':
            break
        consecutive_failures += 1
    require(consecutive_failures < 3, 'no-verdict re-requests exhausted; escalate')


def advance(state, action, p, now, root, *, op_id):
    lc, db, cycle = state['lifecycle'], state['gate_reviews'], state['lifecycle']['outer_cycle']
    result = {'launch_eligible': False}
    if action == hub_publication.ABORT:
        return result | hub_publication.advance(state, action, p, root, op_id)
    if action == consultations.SETTLE:
        # Observations do not resume the project or authorize consuming a result.
        return result | consultations.settle(state, p, root)
    require(lc['status'] != 'suspended' and lc['stage'] != 'COMPLETED', 'project is terminal')
    if action in (hub_publication.PREPARE, knowledge.PUBLISH):
        # A prepared recovery may finish on HOLD; this does not lift HOLD.
        return result | hub_publication.advance(state, action, p, root, op_id)
    if action in ('start-planning', 'gate-review', 'gate-route', 'reuse-readiness', knowledge.ACTION):
        hub_publication.require_idle(state)
    if action in inner_attempts.SETTLEMENTS:
        # Interrupted work may be reconciled on HOLD without authorizing further work.
        return result | inner_attempts.settle(state, action, p, root)
    if action in ('gate-review', 'gate-route', 'reuse-readiness'):
        require('pending_inner_attempt' not in lc, 'reconcile the pending inner attempt before gate progression')
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
    if action == consultations.CONFIGURE:
        return result | consultations.configure(state, p, root)
    if action == consultations.CHECK:
        return result | consultations.record_check(state, p, root)
    require(lc['status'] == 'active' or action == 'record-blocker', 'project is on HOLD')
    if action == hub_publication.BEGIN:
        return result | hub_publication.advance(state, action, p, root, op_id)
    if action == consultations.RESERVE:
        if p.get('purpose') == 'gate':
            hub_publication.require_idle(state)
            manifest = p.get('manifest')
            require(isinstance(manifest, dict) and text(manifest.get('gate')) and text(manifest.get('phase')),
                    'provide an exact gate manifest')
            gate, phase = manifest['gate'], manifest['phase']
            review_slot(state, gate, phase)
            require('pending_inner_attempt' not in lc, 'reconcile the pending inner attempt before gate review')
            check_manifest(manifest, gate, phase, root)
            manifest_identity(state, manifest)
            knowledge.require_current(state, root, manifest, p.get('okf_check'))
            task_readiness.check_gate(state, {'assessment_id': p.get('assessment_id'), 'gate': gate, 'phase': phase}, root)
            if phase == 'readiness':
                check_readiness(state, manifest, root)
            elif phase == 'complete':
                latest_approval(state, 'readiness', root)
        return consultations.reserve(state, p, root)
    if action == consultations.REUSE:
        return result | consultations.reuse(state, p, root)
    if action == 'open-hold':
        require(text(p.get('reason')), 'record a HOLD reason')
        lc.update(status='hold', hold_reason=p['reason'])
    elif action == 'start-scoping':
        require(lc['stage'] == 'CREATED', 'expected CREATED')
        lc['stage'] = 'SCOPING'
    elif action == 'start-planning':
        require(lc['stage'] == 'SCOPING' and text(p.get('charter_ref')), 'expected SCOPING with charter')
        state['identity']['charter_ref'] = p['charter_ref']
        budget = state['budgets']['outer_cycles']
        if budget['used'] == 0:
            budget['used'] = cycle
            result['charged_cycle'] = cycle
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
        result.update(inner_attempts.begin(state, root, op_id))
    elif action == 'return-to-implementation':
        require(lc['stage'] == 'EVALUATING' and text(p.get('reason')), 'record why evaluation requires in-plan rework')
        require(not any(r['cycle'] == cycle and r['route'] is None for r in db.values()), 'resolve the submitted review first')
        latest_approval(state, 'protocol', root)
        verify_artifacts(root, p.get('artifacts'))
        lc['stage'] = 'IMPLEMENTING'
        result.update(rework_reason=p['reason'], rework_artifacts=p['artifacts'])
    elif action == 'reuse-readiness':
        require(lc['stage'] == 'IMPLEMENTING' and not any(r['cycle'] == cycle and r['route'] is None for r in db.values()),
                'reuse requires implementation stage with no awaiting review route')
        key, original = approved_record(state, 'readiness')
        require(p.get('review_id') == key, 'reuse must name the latest routed readiness approval of this cycle')
        current, proof = p.get('manifest'), p.get('proof')
        check_manifest(current, 'PLAN_GATE', 'readiness', root)
        manifest_identity(state, current)
        knowledge.require_current(state, root, current, p.get('okf_check'))
        check_readiness(state, current, root)
        if previous := prior_reuse(state, key):
            old_info = previous['manifest']['readiness']
            inner_attempts.require_first_parent(root, old_info['revision'], current['readiness']['revision'])
            require(inner_attempts.source_commits(root, old_info['revision'], current['readiness']['revision']) and
                    {t['output'] for t in old_info['tests'].values()}.isdisjoint(
                        t['output'] for t in current['readiness']['tests'].values()),
                    'reuse on each additional fix needs a new revision and new passing test outputs')
        check_consumer(state['execution'], key, root)
        check_consumer(state['execution'], op_id, root)
        readiness.check_reuse(state, root, original['manifest'], current, proof)
        lc['stage'] = 'EVALUATING'
        result.update(review_id=key, manifest=current, proof=proof, okf_check=p.get('okf_check'))
    elif action == knowledge.ACTION:
        manifest = p.get('manifest')
        require(isinstance(manifest, dict), 'provide an exact gate manifest for the OKF check')
        gate, phase = manifest.get('gate'), manifest.get('phase')
        check_manifest(manifest, gate, phase, root)
        require(lc['stage'] in STAGE[phase], 'OKF check must target a manifest for the current stage')
        result.update(cycle=cycle, **knowledge.run_gate_check(state, root, manifest, p))
    elif action == 'record-consultation':
        require(ident(p.get('id')) and not any(c['id'] == p['id'] for c in state['consultations']) and
                p.get('agent') in ('research-advisor', 'harness-architector', 'frontend-architector', 'backend-architector') and
                p.get('status') in ('completed', 'no-verdict', 'timeout', 'error') and text(p.get('evidence_ref')) and
                (ident(p.get('run_id')) or (p['status'] != 'completed' and p.get('run_id') is None)),
                'invalid consultation observation')
        if p['agent'] == 'research-advisor':
            accounting = consultations.consume(state, p, root) or {}
        else:
            require('attempt_id' not in p, 'a specialist cannot consume an Advisor attempt')
            accounting = {}
        state['consultations'].append({**p, **accounting, 'kind': 'advice', 'run_id': p.get('run_id'), 'recorded_at': now})
        result['record_id'] = p['id']
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
        require(ident(key) and key not in db and text(gate) and text(phase), 'invalid review ID or gate/phase')
        review_slot(state, gate, phase)
        if 'assessment_id' in p:
            task_readiness.check_gate(state, p, root)
        if phase == 'readiness':
            latest_approval(state, 'protocol', root)
        if phase == 'complete':
            latest_approval(state, 'readiness', root)
        accounting = consultations.consume(state, p, root, gate=True) or {}
        verdict = 'none'
        issue = p.get('failure')
        try:
            require(not issue and accounting.get('usable', True), 'Advisor run did not yield a usable in-limit verdict')
            check_manifest(manifest, gate, phase, root)
            manifest_identity(state, manifest)
            knowledge.require_current(state, root, manifest, p.get('okf_check'))
            if phase == 'readiness':
                check_readiness(state, manifest, root)
            require(ident(run) and not any(r.get('advisor_run_id') == run for r in db.values()) and
                    not any(c.get('run_id') == run and c['kind'] == 'advice' for c in state['consultations']),
                    'unique exact Advisor run ID required; advice is not a verdict')
            check_consumer(state['execution'], key, root)
            verdict = validate_verdict(p.get('verdict'), gate, manifest['id'])
            issue = None
        except (ValueError, OSError, TimeoutExpired) as exc:
            require(text(issue) or p.get('verdict') is not None, 'record a failure reason when no verdict was returned')
            issue = issue or str(exc)
        db[key] = {'cycle': cycle, 'gate': gate, 'phase': phase, 'manifest': manifest, 'verdict': verdict,
                   'output': p.get('verdict'), 'advisor_run_id': run, 'failure': issue, 'route': None, 'at': now,
                   'basis': review_basis(state, phase), 'okf_check': p.get('okf_check'), **accounting}
        if 'assessment_id' in p:
            db[key]['assessment_id'] = p['assessment_id']
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
        consultations.check_review(state, r, root)
        if 'assessment_id' in r:
            task_readiness.check_gate(state, r, root)
        check_manifest(r['manifest'], gate, phase, root)
        okf_check = p.get('okf_check', r.get('okf_check'))
        knowledge.require_current(state, root, r['manifest'], okf_check)
        require(r.get('basis') == review_basis(state, phase), 'gate input state changed; re-review the submission')
        if phase == 'readiness':
            check_readiness(state, r['manifest'], root)
        elif phase == 'complete':
            latest_approval(state, 'readiness', root)
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
        if okf_check:
            r['routed_okf_check'] = okf_check
        result['record_id'] = key
    else:
        raise ValueError(f'unknown lifecycle event: {action}')
    return result


def candidates(state, root):
    lc = state['lifecycle']
    if lc['status'] == 'suspended' or lc['stage'] == 'COMPLETED':
        return []
    if publication := hub_publication.view(state)['pending']:
        return [{'action': 'reconcile-okf-publication', 'basis': 'hub publication is pending', **publication}]
    if pending := lc.get('pending_inner_attempt'):
        return [{'action': 'reconcile-inner-attempt', 'basis': 'implementation accounting is pending', **pending}]
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
              'EVALUATING': ['continue-evaluation-or-review-exit', 'return-to-implementation'], 'ANALYZING': ['review-cycle'], 'REPORTING': ['review-report']}
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
            if r['verdict'] != 'none':
                consultations.check_review(state, r, root)
            require(r['route'] is not None or r.get('basis') == review_basis(state, r['phase']), 'gate input state changed')
            if r['route'] is None and 'assessment_id' in r:
                task_readiness.check_gate(state, r, root)
            if r['phase'] == 'readiness' and r['route'] == 'continue' and prior_reuse(state, key):
                latest_key, _ = approved_record(state, 'readiness')
                require(key == latest_key, 'newer readiness review supersedes this reuse')
                latest_approval(state, 'readiness', root)
            else:
                check_manifest(r['manifest'], r['gate'], r['phase'], root)
                if r['route'] is None and not hub_publication.pending(state):
                    knowledge.require_current(state, root, r['manifest'], r.get('okf_check'))
                if r['phase'] == 'readiness':
                    check_readiness(state, r['manifest'], root)
        except (ValueError, OSError, TimeoutExpired) as exc:
            output.append({'review_id': key, 'reason': str(exc)})
    return output
