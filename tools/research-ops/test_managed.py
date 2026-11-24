"""Offline acceptance/failure-injection tests. Simulated Pi observations, real state and Git."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

from analyze import analyze, draft
from checks import coverage, freshness, manifest, pool_profile
import director
from gate_artifacts import ROLES
import gate_checkpoints
from gates import check_manifest, check_submission
from knowledge import HUB, hub_fingerprint, required as requires_okf
from readiness import source_diff
from task_readiness import DIMENSIONS, TRIGGERS

HERE = Path(__file__).parent.resolve()


class ManagedTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.state = self.root / 'project-state.json'
        self.call('init', self.state, '--project', 'pilot', '--objective', 'Measure quality', '--outer-limit', '3')
        self.rev = 0
        self.op = 0
        self.artifact = self.root / 'artifact.txt'
        self.artifact.write_text('frozen evidence\n')
        self.hashes = {'artifact.txt': hashlib.sha256(self.artifact.read_bytes()).hexdigest()}

    def raw(self, *args, body=None):
        p = subprocess.run([sys.executable, '-B', HERE / 'ledger.py', *args], capture_output=True, text=True,
                           input=json.dumps(body) if body is not None else None)
        self.assertFalse(p.stderr, p.stderr)
        return p.returncode, json.loads(p.stdout)

    def call(self, *args, body=None, valid=True):
        code, out = self.raw(*args, body=body)
        self.assertEqual(code, 0 if valid else 1, out)
        return out

    def args(self, group, action, *, op=None, revision=None):
        if op is None:
            self.op += 1
            op = f'op-{self.op}'
        return ('apply', self.state, group, action, '--input', '-', '--op-id', op, '--actor', 'research-lead',
                '--reason', 'fixture', '--expected-revision', str(self.rev if revision is None else revision))

    def apply(self, action, body, *, group='evidence', valid=True):
        out = self.call(*self.args(group, action), body=body, valid=valid)
        if valid:
            self.rev = out['revision']
        return out

    def lifecycle(self, action, body=None, valid=True):
        body = body or {}
        if valid and action in ('resolve-hold', 'resolve-gate-hold'):
            state = json.loads(self.state.read_text())
            pending = (gate_checkpoints.pending_hold(state) if action == 'resolve-hold' else body.get('id'))
            if pending and state['gate_reviews'].get(pending, {}).get('checkpoint_pending'):
                self.lifecycle(gate_checkpoints.HOLD, {'id': pending})
        if valid and action in gate_checkpoints.ACTIONS:
            args = self.args('lifecycle', action)
            args, body = self.route_commit(args, body)
            out = self.call(*args, body=body)
            self.rev = out['revision']
            return out
        return self.apply(action, body, group='lifecycle', valid=valid)

    def route_commit(self, args, body, *, update_okf=True, omit=()):
        state = json.loads(self.state.read_text())
        action, op = args[3], args[args.index('--op-id') + 1]
        payload = body.copy()
        if action == gate_checkpoints.START:
            charter = self.root / payload['charter_ref']
            if not charter.exists():
                self.fixture_file(payload['charter_ref'], 'fixture active charter\n')
        review = state['gate_reviews'].get(payload.get('review_id' if action == gate_checkpoints.REUSE else 'id'))
        package = payload.get('manifest') if action == gate_checkpoints.REUSE else (review['manifest'] if review else None)
        paths = [self.state.name]
        if action == gate_checkpoints.START:
            paths.append(payload['charter_ref'])
        if action == gate_checkpoints.ROUTE and review['phase'] == 'cycle':
            payload.setdefault('rationale', 'fixture selected route rationale')
        if action != gate_checkpoints.HOLD and package:
            paths.extend(package['artifact_roles'].values())
            if package['phase'] == 'readiness':
                paths.extend(package['readiness']['baseline'])
                paths.extend(t['output'] for t in package['readiness']['tests'].values())
        if action == gate_checkpoints.REUSE:
            paths += [payload['proof']['diff'], *payload['proof']['unchanged'].values()]
        if payload.get('route') == 'stop':
            paths.append(payload['status_report'])
        info = gate_checkpoints.envelope(state, action, payload, op, self.root)
        self.fixture_file(info['decision_path'], info['decision'])
        paths.append(info['decision_path'])
        if update_okf and action != gate_checkpoints.HOLD and package and (requires_okf(package) or payload.get('okf_check')):
            receipt = self.check_okf(package)
            payload['okf_check'] = receipt['op_id']
            paths += [HUB, *receipt['service_artifacts']]
        if not (self.root / '.git').exists():
            self.git('init', '-q')
        self.git('add', '-A', '--', *sorted(set(paths) - set(omit)))
        self.git('commit', '-qm', info['git_subject'])
        payload['checkpoint'] = self.git('rev-parse', 'HEAD')
        return args[:-1] + (str(self.rev),), payload

    def get(self, key):
        return self.call('get', self.state, key)['record']

    def assessment(self, slug='A', **changes):
        return {'beads_task_id': f'pilot-{slug}', 'classification': 'READY',
                'dimensions': {d: 'fixture basis pinned in artifact.txt' for d in DIMENSIONS},
                'uncertainties': [], 'triggers': [], 'artifacts': self.hashes, 'next_step': 'issue bounded brief',
                'routing': {'kind': 'fixed', 'fixed_role': 'engineering-worker', 'assignee': 'engineering-worker',
                            'required': False, 'handoff': 'eligible', 'reason': 'bounded implementation fixture'},
                **changes}

    def assessing(self, slug='A', *, classification='CONSULT', **changes):
        p = self.assessment(slug, classification=classification, **changes)
        del p['routing']
        return p

    def brief_payload(self, slug='A', *, mode='read', previous_revision=None, base=None):
        id_ = f'R-{slug}' + ('-new' if previous_revision else '')
        evidence = {'id': id_, 'assignment_id': f'A-{slug}', 'beads_task_id': f'pilot-{slug}',
                    'assignee': 'engineering-worker', 'mode': mode, 'scope': 'bounded fixture',
                    'deliverable': 'artifact.txt', 'criteria': ['exact observed bytes'],
                    'source_versions': {'input': 'v1'}, 'exclusions': [], 'read_paths': ['artifact.txt'],
                    'modify_paths': [] if mode == 'read' else ['artifact.txt'], 'commands': [] if mode == 'read' else ['git diff --check'],
                    'external_actions': [], 'tools': ['read'], 'attempt_limit': 2, 'soft_seconds': 10, 'hard_seconds': 20}
        if previous_revision:
            evidence['previous_revision'] = previous_revision
        if base:
            evidence['base_revision'] = base
        return evidence

    def brief(self, slug='A', *, mode='read', previous_revision=None, base=None):
        body = self.brief_payload(slug, mode=mode, previous_revision=previous_revision, base=base)
        body['assessment_id'] = self.apply('assess-task', self.assessment(slug))['op_id']
        self.apply('issue', body)
        self.apply('mark-ready', {'id': body['id'], 'basis': 'pinned fixture inputs'})
        return body['id']

    def finish(self, slug='A', *, mode='read', base=None):
        revision = self.brief(slug, mode=mode, base=base)
        a = f'T-{slug}'
        self.apply('reserve', {'id': a, 'revision_id': revision, 'profile_ref': 'fixture-not-real-pi',
                     **({'workspace': str(self.root)} if mode == 'write' else {})})
        self.apply('attach-run', {'id': a, 'run_id': f'pi-{slug}', 'evidence': 'simulated exact match'})
        self.apply('observe-termination', {'id': a, 'evidence': 'simulated process exit'})
        payload = {'id': f'S-{slug}', 'assignment_id': f'A-{slug}', 'revision_id': revision, 'attempt_id': a,
                    'status': 'SUCCESS', 'deliverable': 'artifact.txt', 'evidence_refs': ['artifact.txt'],
                    'gaps': [], 'source_versions': {'input': 'v1'}}
        if mode == 'write':
            payload.update(affected_paths={'artifact.txt': self.hashes['artifact.txt']}, deviations=[], follow_ups=[],
                           verification={'git diff --check': {'exit_code': 0, 'output': 'check exited 0'}})
        self.apply('result', payload)
        self.apply('decision', {'id': f'D-{slug}', 'attempt_id': a, 'result_id': f'S-{slug}',
                               'verdict': 'accepted', 'rationale': 'inspected test evidence'})
        return revision

    def git(self, *args):
        p = subprocess.run(['git', '-C', self.root, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', *args],
                           text=True, capture_output=True, check=True)
        return p.stdout.strip()

    def test_task_assessment_is_required_current_and_auditable_on_dispatch(self):
        body = self.brief_payload()
        self.apply('issue', body, valid=False)
        row = self.apply('assess-task', self.assessment())
        key = row['op_id']
        self.assertFalse(row['launch_eligible'])
        self.assertEqual(self.get(key)['assessment'], self.assessment())
        self.apply('issue', {**body, 'assessment_id': key, 'beads_task_id': 'pilot-other'}, valid=False)
        self.apply('issue', {**body, 'assessment_id': key, 'assignee': 'unapproved-pool',
                             'routing_reason': 'fixture'}, valid=False)
        self.apply('issue', {**body, 'assessment_id': key})
        self.apply('mark-ready', {'id': body['id'], 'basis': 'checked'})
        p = {'id': 'T-1', 'revision_id': body['id'], 'profile_ref': 'fixture'}
        self.artifact.write_text('drift\n')
        self.call('check-task', self.state, key, valid=False)
        self.apply('reserve', p, valid=False)
        self.artifact.write_text('frozen evidence\n')
        self.lifecycle('start-scoping')
        self.apply('reserve', p, valid=False)
        self.assertFalse(self.call('status', self.state)['task_assessments'][0]['current_stage_and_plan'])
        updated = self.brief(previous_revision=body['id'])
        self.assertTrue(self.apply('reserve', {**p, 'revision_id': updated})['launch_eligible'])

    def test_older_brief_can_be_reconciled_but_cannot_dispatch_again_without_assessment(self):
        revision = self.brief()
        self.apply('reserve', {'id': 'T-legacy', 'revision_id': revision, 'profile_ref': 'fixture'})
        snapshot = json.loads(self.state.read_text())
        snapshot['execution']['briefs'][revision].pop('assessment_id')
        self.state.write_text(json.dumps(snapshot))
        self.assertEqual(self.get('T-legacy')['execution'], 'dispatch_pending')
        self.apply('prove-non-dispatch', {'id': 'T-legacy', 'evidence': 'fixture: never submitted'})
        self.apply('reserve', {'id': 'T-new', 'revision_id': revision, 'profile_ref': 'fixture'}, valid=False)
        revised = self.brief(previous_revision=revision)
        self.assertTrue(self.apply('reserve', {'id': 'T-new', 'revision_id': revised, 'profile_ref': 'fixture'})['launch_eligible'])

    def test_task_classes_require_all_dimensions_and_route_fixed_roles_first(self):
        p = self.assessment()
        self.apply('assess-task', {**p, 'dimensions': {'problem': 'only one'}}, valid=False)
        self.apply('assess-task', {**p, 'confidence': 0.95}, valid=False)
        uncertainty = {'kind': 'factual', 'issue': 'what does the primary source say?', 'material': True,
                       'bounded_check': 'read the cited method section'}
        self.apply('assess-task', {**p, 'uncertainties': [uncertainty]}, valid=False)
        investigate = self.assessing(classification='INVESTIGATE', uncertainties=[uncertainty])
        self.apply('assess-task', investigate)
        self.apply('assess-task', {**investigate, 'uncertainties': [{**uncertainty, 'bounded_check': None}]}, valid=False)
        for trigger in TRIGGERS:
            with self.subTest(trigger=trigger):
                self.apply('assess-task', {**p, 'triggers': [trigger]}, valid=False)
        route = p['routing']
        self.apply('assess-task', {**p, 'routing': {**route, 'kind': 'pool', 'assignee': 'pool-test'}}, valid=False)
        self.apply('assess-task', {**p, 'routing': {**route, 'kind': 'lead', 'assignee': None}}, valid=False)
        self.apply('assess-task', {**p, 'routing': {**route, 'kind': 'lead', 'assignee': None,
                   'handoff': 'no-eligible-child', 'required': True}}, valid=False)
        fixed = {**p, 'routing': {**route, 'fixed_role': 'okf-reader', 'assignee': 'okf-reader'}}
        receipt = self.apply('assess-task', fixed)
        self.assertEqual(self.call('check-task', self.state, receipt['op_id'])['routing']['assignee'], 'okf-reader')
        pool = {**p, 'routing': {**route, 'kind': 'pool', 'fixed_role': None, 'assignee': 'pool-test',
                                'reason': 'primary-paper extraction outside fixed scopes'}}
        pool_id = self.apply('assess-task', pool)['op_id']
        self.call('check-task', self.state, receipt['op_id'], valid=False)
        brief = {**self.brief_payload(), 'assignee': 'pool-test', 'assessment_id': pool_id}
        self.apply('issue', {**brief, 'routing_reason': 'conflicting basis'}, valid=False)
        self.apply('issue', {**brief, 'routing_reason': 'primary-paper extraction outside fixed scopes'})
        direct = {**p, 'routing': {**route, 'kind': 'lead', 'assignee': None, 'handoff': 'coupled',
                                  'reason': 'deciding how to reconcile two validity claims is Lead judgment'}}
        key = self.apply('assess-task', direct)['op_id']
        self.assertEqual(self.call('check-task', self.state, key)['routing']['kind'], 'lead')

    def test_mandatory_task_advice_survives_a_block_and_needs_exact_completed_disposition(self):
        consult = self.apply('assess-task', self.assessing(triggers=['contradictory-evidence']))['op_id']
        self.apply('assess-task', self.assessing(classification='BLOCKED', next_step='ask Director about data access'))
        self.assertEqual(self.call('next', self.state)['task_assessments'][0]['pending_advisor'], [consult])
        self.apply('assess-task', self.assessment(), valid=False)
        advice_file = self.root / 'advice.txt'
        advice_file.write_text('fixture advice\n')
        artifacts = {'advice.txt': hashlib.sha256(advice_file.read_bytes()).hexdigest()}
        advice = {'id': 'advice-1', 'agent': 'research-advisor', 'run_id': 'simulated-advisor-run',
                  'status': 'completed', 'evidence_ref': 'advice.txt', 'artifacts': artifacts,
                  'assessment_id': consult}
        self.lifecycle('record-consultation', advice, valid=False)
        self.lifecycle('record-consultation', {**advice, 'agent': 'backend-architector',
                       'disposition': 'accepted', 'rationale': 'fixture'}, valid=False)
        self.lifecycle('record-consultation', {**advice, 'id': 'timeout-1', 'status': 'timeout', 'run_id': None})
        self.apply('assess-task', self.assessment(), valid=False)
        self.lifecycle('record-consultation', {**advice, 'disposition': 'adapted', 'rationale': 'fixture decision'})
        another = self.apply('assess-task', self.assessing('B'))['op_id']
        self.lifecycle('record-consultation', {**advice, 'id': 'advice-2', 'assessment_id': another,
                       'disposition': 'adapted', 'rationale': 'fixture decision'}, valid=False)
        ready = self.apply('assess-task', self.assessment())
        self.assertEqual(ready['resolved_advisor'], {consult: 'advice-1'})
        self.call('check-task', self.state, ready['op_id'])
        advice_file.write_text('changed since reviewed\n')
        self.call('check-task', self.state, ready['op_id'], valid=False)

    def advisor_policy(self, *, mandatory=4, exploratory=1, per_issue=2, version='1'):
        per_call = {'tokens': 120, 'model_calls': 3, 'seconds': 20}
        lanes = {key: {'calls': n, 'attempts_per_issue': per_issue, 'per_call': per_call}
                 for key, n in (('mandatory', mandatory), ('exploratory', exploratory))}
        path = self.root / f'fixture-approval-{version}.json'
        path.write_text(json.dumps({'operator': 'fixture-only', 'id': f'fixture-approval-{version}', **lanes}))
        return {**lanes, 'approval': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()}}

    def advisor_request(self, assessment_id, purpose='exploratory', **more):
        return {'assessment_id': assessment_id, 'purpose': purpose, 'pass': 'decision', 'brief': self.hashes,
                'limits': {'tokens': 100, 'model_calls': 2, 'seconds': 15}, **more}

    def explore(self, slug='A'):
        assessment = self.apply('assess-task', self.assessment(slug))['op_id']
        return self.advisor_request(assessment, inputs={'question': 'Would the simpler test improve diagnostics?',
                    'assumptions': ['same benchmark'], 'constraints': ['no external changes'], 'artifacts': self.hashes})

    def settle_advisor(self, attempt_id, run_id=None, *, outcome='finished', tokens=60, valid=True):
        measured = {'tokens': tokens, 'model_calls': 1, 'seconds': 3} if outcome != 'non-dispatched' else {
            'tokens': 0, 'model_calls': 0, 'seconds': 0}
        return self.lifecycle('settle-consultation', {'attempt_id': attempt_id, 'outcome': outcome, 'run_id': run_id,
                              'usage': measured, 'artifacts': self.hashes}, valid=valid)

    def advisor_result(self, attempt, run_id, *, slug='advice', **kwargs):
        file = self.root / f'{slug}.txt'
        file.write_text('fixture Advisor findings\n')
        return {'id': slug, 'agent': 'research-advisor', 'status': 'completed', 'run_id': run_id, 'attempt_id': attempt,
                'evidence_ref': file.name, 'artifacts': {file.name: hashlib.sha256(file.read_bytes()).hexdigest()},
                'disposition': 'adapted', 'rationale': 'Lead assessment of fixture findings', **kwargs}

    def test_exhausted_exploration_does_not_consume_mandatory_gate_budget(self):
        request = self.explore()
        self.lifecycle('reserve-consultation', request, valid=False)
        self.lifecycle('configure-consultations', self.advisor_policy(mandatory=2))
        opt = self.lifecycle('reserve-consultation', request)['op_id']
        self.settle_advisor(opt, 'run-timeout', outcome='timed-out', tokens=None)
        optional_again = self.explore('other')
        self.lifecycle('reserve-consultation', optional_again, valid=False)
        self.lifecycle('start-scoping')
        self.lifecycle('start-planning', {'charter_ref': 'charter.md'})
        target = {'gate': 'PLAN_GATE', 'phase': 'protocol'}
        assessment = self.apply('assess-task', self.assessing('gate', triggers=['stage-review-gate'], gate=target))['op_id']
        manifest = self.gate_manifest('protocol', 'real-review')
        request = self.advisor_request(assessment, 'gate', manifest=manifest)
        prepass = self.lifecycle('reserve-consultation', {**request, 'pass': 'evidence-first'})['op_id']
        self.settle_advisor(prepass, 'run-first-pass')
        self.review('protocol', 'first-pass', valid=False, assessment_id=assessment, attempt_id=prepass, run_id='run-first-pass')
        self.lifecycle('record-consultation', self.advisor_result(prepass, 'run-first-pass'))
        self.review('protocol', 'unaccounted', valid=False, assessment_id=assessment)
        decision = self.lifecycle('reserve-consultation', request)['op_id']
        self.settle_advisor(decision, 'run-real-review')
        self.review('protocol', 'wrong-manifest', valid=False, assessment_id=assessment, attempt_id=decision, run_id='run-real-review')
        self.review('protocol', 'real-review', assessment_id=assessment, attempt_id=decision)
        self.assertEqual(self.get('real-review')['attempt_id'], decision)
        view = self.call('status', self.state)['advisor_calls']
        self.assertEqual(view['lanes']['mandatory']['charged'], 2)
        self.assertEqual(view['lanes']['exploratory']['missing_usage']['tokens'], 1)

    def test_retry_limit_survives_restart_and_changed_brief_and_releases_only_verified_non_dispatch(self):
        self.lifecycle('configure-consultations', self.advisor_policy(exploratory=3, per_issue=1))
        request = self.explore()
        args = self.args('lifecycle', 'reserve-consultation')
        result = self.call(*args, body=request)
        self.rev = result['revision']
        key = result['op_id']
        self.assertTrue(result['launch_eligible'])
        self.assertFalse(self.call(*args, body=request)['launch_eligible'])
        self.assertEqual(self.call('next', self.state)['advisor_calls']['outstanding'], [key])
        self.lifecycle('reserve-consultation', request, valid=False)
        self.settle_advisor(key, 'not-a-release', outcome='non-dispatched', valid=False)
        self.lifecycle('open-hold', {'reason': 'fixture interruption'})
        self.settle_advisor(key, outcome='non-dispatched')
        self.assertEqual(self.call('status', self.state)['status'], 'hold')
        self.lifecycle('resolve-hold', {'resolution': 'test no launch'})
        retry = self.lifecycle('reserve-consultation', request)['op_id']
        self.settle_advisor(retry, 'run-retry', outcome='timed-out')
        revised = self.explore()
        self.lifecycle('reserve-consultation', revised, valid=False)
        other = self.explore('other')
        self.lifecycle('reserve-consultation', other)
        self.assertEqual(self.call('status', self.state)['advisor_calls']['lanes']['exploratory']['charged'], 2)

    def test_gate_cannot_advance_on_unmeasured_usage(self):
        self.lifecycle('configure-consultations', self.advisor_policy())
        self.lifecycle('start-scoping')
        self.lifecycle('start-planning', {'charter_ref': 'charter.md'})
        target = {'gate': 'PLAN_GATE', 'phase': 'protocol'}
        key = self.apply('assess-task', self.assessing('gate', triggers=['stage-review-gate'], gate=target))['op_id']
        manifest = self.gate_manifest('protocol', 'uncounted')
        attempt = self.lifecycle('reserve-consultation', self.advisor_request(key, 'gate', manifest=manifest))['op_id']
        self.settle_advisor(attempt, 'run-uncounted', tokens=None)
        review = self.review('protocol', 'uncounted', assessment_id=key, attempt_id=attempt, route=None)
        self.assertEqual(review['verdict'], 'none')
        self.assertEqual(self.call('status', self.state)['status'], 'active')
        self.assertEqual(self.call('status', self.state)['gate_holds'][0]['id'], 'uncounted')
        self.lifecycle('gate-route', {'id': 'uncounted', 'route': 'continue'}, valid=False)
        self.lifecycle('gate-review', {'id': 'same-gate-retry', 'gate': 'PLAN_GATE', 'phase': 'protocol'}, valid=False)
        self.resolve_gate_hold('uncounted')

    def test_limits_preserve_actual_overrun_and_need_new_pinned_operator_decision(self):
        policy = self.advisor_policy(exploratory=2)
        self.lifecycle('configure-consultations', {**policy, 'exploratory': {**policy['exploratory'], 'calls': 99}}, valid=False)
        self.lifecycle('configure-consultations', policy)
        request = self.explore()
        self.lifecycle('reserve-consultation', {**request, 'limits': {**request['limits'], 'tokens': 121}}, valid=False)
        key = self.lifecycle('reserve-consultation', request)['op_id']
        self.lifecycle('configure-consultations', self.advisor_policy(exploratory=3, version='2'), valid=False)
        result = self.settle_advisor(key, 'run-overrun', tokens=101)
        self.assertEqual(result['over_limit'], ['tokens'])
        self.lifecycle('record-consultation', self.advisor_result(key, 'run-overrun'), valid=False)
        other = self.explore('other')
        self.lifecycle('reserve-consultation', other, valid=False)
        self.lifecycle('configure-consultations', policy, valid=False)
        replacement = self.advisor_policy(exploratory=2, version='3')
        self.lifecycle('configure-consultations', replacement)
        self.lifecycle('reserve-consultation', other)
        view = self.call('status', self.state)['advisor_calls']
        self.assertEqual(view['lanes']['exploratory']['charged'], 2)
        self.assertEqual(view['lanes']['exploratory']['observed_usage']['tokens'], 101)

    def test_reuse_is_exact_exploratory_only_and_invalidated_by_contradiction(self):
        self.lifecycle('configure-consultations', self.advisor_policy())
        request = self.explore()
        attempt = self.lifecycle('reserve-consultation', request)['op_id']
        self.settle_advisor(attempt, 'run-advice')
        result = self.advisor_result(attempt, 'run-advice')
        self.lifecycle('record-consultation', result)
        self.lifecycle('record-consultation', {**result, 'id': 'duplicate-advice'}, valid=False)
        reuse = {k: request[k] for k in ('assessment_id', 'inputs')} | {'consultation_id': 'advice', 'rationale': 'same decision'}
        successful = self.lifecycle('reuse-consultation', reuse)
        self.assertEqual(successful['source_attempt'], attempt)
        self.assertFalse(successful['launch_eligible'])
        for changes in ({'question': 'different'}, {'assumptions': ['different']}, {'constraints': ['different']}):
            self.lifecycle('reuse-consultation', {**reuse, 'inputs': {**reuse['inputs'], **changes}}, valid=False)
        (self.root / 'advice.txt').write_text('drift')
        self.lifecycle('reuse-consultation', reuse, valid=False)
        self.advisor_result(attempt, 'run-advice')  # Restore pinned output.
        task = self.apply('assess-task', self.assessing(triggers=['contradictory-evidence']))['op_id']
        self.lifecycle('reuse-consultation', {**reuse, 'assessment_id': task}, valid=False)
        required = self.lifecycle('reserve-consultation', self.advisor_request(task, 'task-advice'))['op_id']
        self.settle_advisor(required, 'run-required')
        self.lifecycle('record-consultation', self.advisor_result(required, 'run-required', slug='required', assessment_id=task))
        new_assessment = self.apply('assess-task', self.assessment())['op_id']
        reuse['assessment_id'] = new_assessment
        self.lifecycle('reuse-consultation', {**reuse, 'consultation_id': 'required'}, valid=False)
        self.lifecycle('record-advice-check', {'consultation_id': 'advice', 'finding': 'contradicted', 'rationale': 'test observation',
                                               'artifacts': self.hashes})
        self.lifecycle('reuse-consultation', reuse, valid=False)
        self.assertEqual(self.call('status', self.state)['advisor_calls']['lanes']['exploratory']['charged'], 1)

    def test_fresh_reservation_exact_replay_and_restart_gap(self):
        r = self.brief()
        p = {'id': 'T-1', 'revision_id': r, 'profile_ref': 'fixture'}
        a = self.args('evidence', 'reserve')
        receipt = self.call(*a, body=p)
        self.rev = receipt['revision']
        self.assertTrue(receipt['launch_eligible'])
        ops = self.call('show', 'operations', self.state)
        self.assertFalse(ops[receipt['op_id']]['launch_eligible'])
        self.assertFalse(self.call(*a, body=p)['launch_eligible'])
        self.assertTrue(self.call(*a, body=p)['replayed'])
        self.call(*a, body={**p, 'id': 'T-2'}, valid=False)
        self.apply('launch-unknown', {'id': 'T-1', 'evidence': 'resume without returned ID'})
        self.apply('reserve', {**p, 'id': 'T-2'}, valid=False)
        independent = self.brief('B')
        self.apply('reserve', {'id': 'T-B', 'revision_id': independent, 'profile_ref': 'fixture'})
        self.apply('prove-non-dispatch', {'id': 'T-1', 'evidence': 'simulated confirmed pre-submit interruption'})
        self.apply('reserve', {**p, 'id': 'T-2'})
        self.assertEqual(self.get('T-1')['execution'], 'not_dispatched')

    def test_two_concurrent_reservations_only_one_commits(self):
        r = self.brief()
        calls = [(self.args('evidence', 'reserve'), {'id': f'T-{i}', 'revision_id': r, 'profile_ref': 'fixture'}) for i in (1, 2)]
        with ThreadPoolExecutor(2) as executor:
            codes = list(executor.map(lambda entry: self.raw(*entry[0], body=entry[1])[0], calls))
        self.assertEqual(sorted(codes), [0, 1])
        self.assertEqual(len(self.call('status', self.state)['execution']['open_attempts']), 1)

    def test_partial_and_unrun_worker_checks_cannot_be_accepted(self):
        self.git('init', '-q')
        self.git('add', 'artifact.txt')
        self.git('commit', '-qm', 'base')
        base = self.git('rev-parse', 'HEAD')
        brief = self.brief_payload('claims-unrun', mode='write', base=base)
        brief['assessment_id'] = self.apply('assess-task', self.assessment('claims-unrun'))['op_id']
        self.apply('issue', brief)
        self.apply('mark-ready', {'id': brief['id'], 'basis': 'fixture write assessment'})
        for attempt_id, result_id, status in (('partial-attempt', 'partial-result', 'PARTIAL'),
                                               ('unrun-attempt', 'unrun-result', 'SUCCESS')):
            self.apply('reserve', {'id': attempt_id, 'revision_id': brief['id'], 'profile_ref': 'fixture',
                                   'workspace': str(self.root)})
            self.apply('attach-run', {'id': attempt_id, 'run_id': f'run-{attempt_id}', 'evidence': 'fixture launch'})
            self.apply('observe-termination', {'id': attempt_id, 'evidence': 'fixture exit observed'})
            self.apply('reconcile-effects', {'id': attempt_id, 'disposition': 'clean', 'evidence': 'fixture clean workspace'})
            result = {'id': result_id, 'assignment_id': brief['assignment_id'], 'revision_id': brief['id'],
                      'attempt_id': attempt_id, 'status': status, 'source_versions': brief['source_versions'],
                      'deliverable': 'artifact.txt', 'evidence_refs': ['artifact.txt'], 'gaps': ['fixture incomplete'],
                      'affected_paths': {}, 'deviations': [], 'follow_ups': [],
                      'verification': {'git diff --check': {'not_run': 'fixture child did not return the check'}}}
            self.apply('result', result)
            accepted = self.apply('decision', {'id': f'accepted-{attempt_id}', 'attempt_id': attempt_id,
                                               'result_id': result_id, 'verdict': 'accepted',
                                               'rationale': 'fixture falsification probe'}, valid=False)
            expected = ('timely SUCCESS' if status == 'PARTIAL' else 'verification failed or was not run')
            self.assertIn(expected, accepted['refused'])
            rejected = self.apply('decision', {'id': f'rejected-{attempt_id}', 'attempt_id': attempt_id,
                                               'result_id': result_id, 'verdict': 'rejected',
                                               'rationale': 'unrun verification is not evidence'})
            self.assertEqual(self.get(f'rejected-{attempt_id}')['verdict'], 'rejected')

    def test_write_acceptance_is_not_integration_or_task_closure(self):
        self.git('init', '-q')
        self.git('add', 'artifact.txt')
        self.git('commit', '-qm', 'base')
        base = self.git('rev-parse', 'HEAD')
        self.artifact.write_text('workspace run output\n')
        self.hashes['artifact.txt'] = hashlib.sha256(self.artifact.read_bytes()).hexdigest()
        self.finish(mode='write', base=base)
        self.call('check-close', self.state, 'pilot-A', 'D-A', 'accepted', valid=False)
        p = {'id': 'I-A', 'decision_id': 'D-A', 'artifacts': self.hashes, 'checkpoint': base}
        self.apply('record-availability', p, valid=False)
        self.git('add', 'artifact.txt')
        self.git('commit', '-qm', 'verified delivery')
        self.apply('reconcile-effects', {'id': 'T-A', 'disposition': 'integrated', 'evidence': 'inspected exact Git diff'})
        self.apply('record-availability', p, valid=False)  # An ancestor alone is not the checkpoint of the accepted bytes.
        self.apply('record-availability', {**p, 'checkpoint': self.git('rev-parse', 'HEAD')})
        self.assertTrue(self.call('check-close', self.state, 'pilot-A', 'D-A', 'accepted')['allowed'])
        self.artifact.write_text('unintegrated new bytes')
        self.call('check-close', self.state, 'pilot-A', 'D-A', 'accepted', valid=False)

    def test_cutoff_does_not_prove_exit_wrong_and_late_result_cannot_complete(self):
        r = self.brief()
        p = {'id': 'T-1', 'revision_id': r, 'profile_ref': 'fixture'}
        self.apply('reserve', p)
        self.apply('attach-run', {'id': 'T-1', 'run_id': 'pi-1', 'evidence': 'run receipt'})
        self.apply('hard-cutoff', {'id': 'T-1', 'evidence': 'no usable result at cutoff'})
        self.apply('reserve', {**p, 'id': 'T-2'}, valid=False)
        self.apply('observe-termination', {'id': 'T-1', 'evidence': 'simulated separately observed exit'})
        result = {'id': 'S-1', 'assignment_id': 'A-A', 'revision_id': r, 'attempt_id': 'T-1', 'status': 'SUCCESS',
                  'deliverable': 'artifact.txt', 'evidence_refs': ['artifact.txt'], 'gaps': [], 'source_versions': {'input': 'v1'}}
        self.apply('result', {**result, 'revision_id': 'wrong'}, valid=False)
        self.apply('result', result)
        self.assertTrue(self.get('S-1')['late'])
        self.apply('decision', {'id': 'D-A', 'attempt_id': 'T-1', 'result_id': 'S-1',
                                'verdict': 'accepted', 'rationale': 'should refuse'}, valid=False)

    def test_supersession_preserves_history_and_flags_transitive_use(self):
        self.finish()
        self.apply('record-availability', {'id': 'I-A', 'decision_id': 'D-A', 'artifacts': self.hashes})
        self.finish('B')
        self.apply('pin-use', {'id': 'U-1', 'consumer': 'R-B', 'decision_id': 'D-A', 'output': 'artifact.txt', 'required': True})
        self.apply('record-availability', {'id': 'I-B', 'decision_id': 'D-B', 'artifacts': self.hashes})
        self.apply('pin-use', {'id': 'U-2', 'consumer': 'gate-42', 'decision_id': 'D-B', 'output': 'artifact.txt', 'required': True})
        self.apply('decision', {'id': 'D-C', 'attempt_id': 'T-A', 'supersedes': 'D-A', 'verdict': 'rejected',
                                'rationale': 'newly discovered defect'})
        self.assertEqual(self.get('D-A')['verdict'], 'accepted')
        self.assertEqual(self.call('status', self.state)['execution']['revalidate'], ['R-B', 'gate-42'])
        self.call('check-close', self.state, 'pilot-B', 'D-B', 'accepted', valid=False)

    def fixture_file(self, relative, data):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data if isinstance(data, str) else json.dumps(data))
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def gate_manifest(self, phase, slug, *, route=None, extra=None):
        if phase == 'readiness':
            return self.readiness_manifest(slug) | (extra or {})
        phase_data = self.gate_evidence(phase, slug, route=route, extra=extra)
        gate = {'protocol': 'PLAN_GATE', 'complete': 'INNER_EXIT_GATE', 'diagnosis': 'INNER_EXIT_GATE',
                'cycle': 'CYCLE_GATE', 'report': 'REPORT_GATE'}[phase]
        base = {'gate': gate, 'phase': phase, 'id': f'{slug}@v1'}
        if phase == 'protocol':
            base['required_tests'] = ['unit']
        return base | phase_data | (extra or {})

    def gate_evidence(self, phase, slug, *, route=None, extra=None):
        artifacts, roles = self.hashes.copy(), {}
        for role in ROLES[phase]:
            path = 'charter.md' if role == 'charter' else f'gate-evidence/{phase}/{role}.md'
            roles[role] = path
            if role not in ('final-manifest', 'verification', 'cycle-decision'):
                artifacts[path] = self.fixture_file(path, f'fixture {phase} evidence: {role}\n')
        meta = {}
        if phase == 'diagnosis':
            meta['diagnosis'] = {'reason': 'requires-plan-change', 'gaps': ['no valid treatment results'],
                                 'rationale': 'fixture protocol cannot test the treatment'}
        elif phase == 'cycle':
            lc = json.loads(self.state.read_text())['lifecycle']
            route = (extra or {}).get('proposed_route', route if route in ('replan', 'report', 'stop') else 'hold')
            meta['proposed_route'] = route
            meta.update({k: extra[k] for k in ('next_plan', 'replan_rationale') if extra and k in extra})
            path = roles['cycle-decision'] = f'gate-evidence/cycle/{slug}-cycle-decision.json'
            artifacts[path] = self.fixture_file(path, {'id': slug, 'cycle': lc['outer_cycle'],
                'plan_version': lc['plan_version'], 'rationale': 'fixture cycle decision', 'evidence_refs': ['artifact.txt'], **meta})
        elif phase == 'report':
            pins = {path: artifacts[path] for role, path in roles.items() if role not in ('final-manifest', 'verification')}
            path = roles['final-manifest'] = 'gate-evidence/report/final-artifact-manifest.json'
            artifacts[path] = self.fixture_file(path, {'artifacts': pins | self.hashes})
            path = roles['verification'] = 'gate-evidence/report/independent-verification.json'
            artifacts[path] = self.fixture_file(path, {'verifier': 'fixture-only', 'method': 'fixture inspection',
                'artifacts': pins | {roles['final-manifest']: artifacts[roles['final-manifest']]}})
        return {'artifacts': artifacts, 'artifact_roles': roles, **meta}

    def readiness_manifest(self, slug):
        protocol = next(key for key, record in reversed(self.call('show', 'gate_reviews', self.state).items())
                        if record['phase'] == 'protocol' and record['route'] == 'continue')
        output = self.root / f'{slug}-tests.log'
        output.write_text(f'fixture test observations for {slug}\n')
        baseline = self.root / 'src/method.py'
        evidence = self.gate_evidence('readiness', slug)
        evidence['artifacts'].update({p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in (output, baseline)})
        return {'id': f'{slug}@v1', 'gate': 'PLAN_GATE', 'phase': 'readiness', **evidence,
                'readiness': {'revision': self.git('rev-parse', 'HEAD'), 'protocol_review': protocol,
                              'baseline': ['src/method.py'], 'tests': {'unit': {'exit_code': 0, 'output': output.name}}}}

    def seed_okf(self):
        hub = self.root / HUB
        hub.mkdir(exist_ok=True)
        index = hub / 'index.md'
        if not index.exists():
            index.write_text('---\nokf_version: "0.2"\n---\n# Fixture hub\n- [Note](note.md)\n')
            (hub / 'note.md').write_text('---\ntype: Note\n---\nFixture records.\n')
        return hub

    def begin_okf(self, *paths):
        hub = self.seed_okf()
        request = self.lifecycle('begin-okf-publication', {'paths': list(paths), 'request_artifacts': self.hashes})
        shutil.copytree(hub, self.root / request['staging'])
        return request

    def prepare_okf(self, request, *, created=(), updated=(), writer_bytes=None, valid=True):
        writer = self.root / f"writer-{request['op_id']}.json"
        writer.write_bytes(writer_bytes if writer_bytes is not None else json.dumps({
            'status': 'committed', 'created': list(created), 'updated': list(updated), 'deprecated': [],
            'evidence': ['fixture'], 'validation': [{'check': 'bundle', 'result': 'passed'}], 'warnings': [],
            'revision': {'state': 'fixture snapshot', 'git_commit_made': False},
        }).encode())
        return self.lifecycle('prepare-okf-publication', {'request_id': request['op_id'], 'writer_result': writer.name,
                              'writer_artifacts': {writer.name: hashlib.sha256(writer.read_bytes()).hexdigest()}}, valid=valid)

    def publish_okf(self, request):
        return self.lifecycle('publish-okf', {'request_id': request['op_id']})

    def stage_director_documents(self, request, *decision_ids, index_decisions=True):
        state = json.loads(self.state.read_text())
        stage = self.root / request['staging']
        index = stage / 'index.md'
        links = index.read_text()
        brief_link = '- [Director brief](director-brief.md)\n'
        if brief_link not in links:
            links += brief_link
        replacements = {'director-brief.md': '---\ntype: director-brief\n---\n# Standing brief\n' + director.brief_marker(state) + '\n'}
        for key in decision_ids:
            name = director.path_for(key)
            link = f'- [Decision {key}]({name})\n'
            if index_decisions and link not in links:
                links += link
            elif not index_decisions:
                links = links.replace(link, '')
            replacements['director-brief.md'] += link
            replacements[name] = ('---\ntype: director-decision\n---\n# Decision fixture\n' +
                                  director.marker(director.get(state, key)) + '\n')
        replacements['index.md'] = links
        created, updated = [], []
        for name, data in replacements.items():
            path = stage / name
            if not path.exists():
                created.append(name)
            elif path.read_text() == data:
                continue
            else:
                updated.append(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(data)
        return {'created': created, 'updated': updated}

    def publish_director(self, *keys, index_decisions=True):
        request = self.begin_okf('index.md', 'director-brief.md', *(director.path_for(key) for key in keys))
        self.prepare_okf(request, **self.stage_director_documents(request, *keys, index_decisions=index_decisions))
        return self.publish_okf(request)['op_id']

    def check_okf(self, manifest, *, publication=None, valid=True, reader_status=None,
                  reader_evidence=True, reader_snapshot=True):
        if publication is None:
            if manifest['phase'] in ('cycle', 'report'):
                request = self.begin_okf('index.md', 'director-brief.md')
                self.prepare_okf(request, **self.stage_director_documents(request))
            else:
                request = self.begin_okf()
                self.prepare_okf(request)
            publication = self.publish_okf(request)
        writer = publication['writer_result']
        service_artifacts = {writer: publication['writer_artifacts'][writer]}
        body = {'manifest': manifest, 'writer_result': writer, 'publication_id': publication['op_id'],
                'hub_sha256': hub_fingerprint(self.root), 'service_artifacts': service_artifacts}
        if reader_status is not None:
            reader = self.root / f'reader-{self.op + 1}.json'
            index = self.root / HUB / 'index.md'
            payload = {'status': reader_status, 'answer': 'Fixture evidence packet',
                       'evidence': ([{'conceptPath': 'note.md', 'support': 'Fixture primary concept evidence',
                                      'rationale': 'Directly supports the requested retrieval.'}] if reader_evidence else []),
                       'gaps': [], 'search': {'scope': 'fixture bundle', 'queries': ['fixture'],
                          'searched_paths': ['note.md'], 'excluded': [], 'truncated': False, 'stop_reason': 'fixture scope exhausted'},
                       'revision': {'state': 'fixture', **({'bundle_sha256': hub_fingerprint(self.root)} if reader_snapshot else {})}}
            reader.write_text(json.dumps(payload))
            body.update(reader_result=reader.name)
            body['service_artifacts'][reader.name] = hashlib.sha256(reader.read_bytes()).hexdigest()
        return self.lifecycle('check-okf-gate', body, valid=valid)

    def review(self, phase, slug, *, verdict='approve', route='continue', extra=None, valid=True, check_okf=True,
               assessment_id=None, attempt_id=None, run_id=None, failure=None):
        m = self.gate_manifest(phase, slug, route=route, extra=extra)
        gate = m['gate']
        output = {'gate': gate, 'review_target': m['id'], 'verdict': verdict, 'summary': 'synthetic review fixture',
                  'findings': [], 'alternative_explanations': [], 'residual_uncertainties': [],
                  'recommended_next_actions': [], 'additional_evidence_required': []}
        if verdict in ('revise', 'block'):
            output['findings'] = [{'severity': 'major', 'issue': 'fixture gap', 'justification': 'check',
                                   'evidence_refs': ['artifact.txt'], 'required_action': 'triage'}]
        if verdict == 'inconclusive':
            output['additional_evidence_required'] = ['fixture']
        payload = {'id': slug, 'gate': gate, 'phase': phase, 'manifest': m,
                   'advisor_run_id': None if failure else (run_id or f'run-{slug}'), 'verdict': output}
        if failure:
            payload['failure'] = failure
        if assessment_id:
            payload['assessment_id'] = assessment_id
        if attempt_id:
            payload['attempt_id'] = attempt_id
        if valid and check_okf and requires_okf(m):
            payload['okf_check'] = self.check_okf(m, reader_status='sufficient' if m.get('okf_reader_required') else None)['op_id']
        out = self.lifecycle('gate-review', payload, valid=valid)
        if route and valid:
            self.lifecycle('gate-route', {'id': slug, 'route': route})
        return out

    def test_stage_review_assessment_only_resolves_through_its_gate_and_handles_drift(self):
        self.lifecycle('start-scoping')
        self.lifecycle('start-planning', {'charter_ref': 'charter.md'})
        gate = {'gate': 'PLAN_GATE', 'phase': 'protocol'}
        draft = self.assessing(triggers=['stage-review-gate'], gate=gate)
        self.apply('assess-task', {**draft, 'gate': {**gate, 'phase': 'readiness'}}, valid=False)
        gate_input = self.root / 'review-input.md'
        gate_input.write_text('v1\n')
        draft['artifacts'] = {gate_input.name: hashlib.sha256(gate_input.read_bytes()).hexdigest()}
        first = self.apply('assess-task', draft)['op_id']
        self.apply('assess-task', self.assessment(), valid=False)
        self.review('protocol', 'check-v1', route=None, assessment_id=first)
        self.apply('assess-task', self.assessment(), valid=False)  # Verdict not routed yet.
        gate_input.write_text('v2\n')
        self.lifecycle('gate-route', {'id': 'check-v1', 'route': 'continue'}, valid=False)
        self.assertEqual(self.call('next', self.state)['candidates'][0]['action'], 'withdraw-stale-review')
        self.lifecycle('withdraw-stale-review', {'id': 'check-v1'})
        second = self.apply('assess-task', {**draft, 'artifacts': {gate_input.name:
                            hashlib.sha256(gate_input.read_bytes()).hexdigest()}})['op_id']
        self.review('protocol', 'check-v2', assessment_id=second)
        self.assertEqual(self.call('status', self.state)['task_assessments'][0]['pending_advisor'], [])
        ready = self.apply('assess-task', self.assessment())
        self.assertEqual(ready['resolved_advisor'], {first: 'check-v2', second: 'check-v2'})

    def init_cycle_workspace(self):
        self.git('init', '-q')
        (self.root / 'src').mkdir()
        (self.root / 'src/method.py').write_text('initial baseline\n')
        self.git('add', 'artifact.txt', 'src')
        self.git('commit', '-qm', 'base')

    def settle_payload(self, started):
        return {'start_op_id': started['op_id'], 'checkpoint': self.git('rev-parse', 'HEAD')}

    def commit_implementation(self, contents):
        (self.root / 'src/method.py').write_text(contents)
        self.git('add', 'src')
        self.git('commit', '-qm', 'integrate implementation')

    def integrate_attempt(self, contents):
        started = self.lifecycle('begin-inner-attempt')
        self.commit_implementation(contents)
        self.lifecycle('record-inner-integration', self.settle_payload(started))

    def start_implementation(self):
        self.init_cycle_workspace()
        self.lifecycle('start-scoping')
        self.lifecycle('start-planning', {'charter_ref': 'charter.md'})
        self.review('protocol', 'protocol')

    def open_cycle(self, suffix, initial=False):
        if initial:
            self.init_cycle_workspace()
            self.lifecycle('start-scoping')
            self.lifecycle('start-planning', {'charter_ref': 'charter.md'})
        self.review('protocol', f'protocol-{suffix}')
        self.lifecycle('gate-route', {'id': f'protocol-{suffix}', 'route': 'continue'}, valid=False)
        self.integrate_attempt(f'method for cycle {suffix}\n')
        self.review('readiness', f'readiness-{suffix}')
        self.review('complete', f'exit-{suffix}')

    def test_inner_integration_charges_once_even_if_evaluation_never_started(self):
        self.start_implementation()
        self.review('readiness', 'unrouted-readiness', route=None)
        started = self.lifecycle('begin-inner-attempt')
        view = self.call('status', self.state)
        self.assertEqual(view['inner_attempt'], 0)
        self.assertEqual(view['pending_inner_attempt']['start_op_id'], started['op_id'])
        self.assertEqual(self.call('next', self.state)['candidates'][0]['action'], 'reconcile-inner-attempt')
        self.lifecycle('begin-inner-attempt', valid=False)
        self.lifecycle('gate-route', {'id': 'unrouted-readiness', 'route': 'continue'}, valid=False)
        self.review('diagnosis', 'premature-exit', valid=False)
        base = self.settle_payload(started)
        self.lifecycle('record-inner-integration', base, valid=False)
        self.commit_implementation('new method\n')
        self.lifecycle('record-inner-integration', base, valid=False)  # Not the current HEAD.
        payload = self.settle_payload(started)
        self.lifecycle('record-inner-integration', {**payload, 'start_op_id': 'other'}, valid=False)
        self.lifecycle('record-no-change-interruption', payload, valid=False)
        self.lifecycle('open-hold', {'reason': 'interrupted before evaluation'})

        args = self.args('lifecycle', 'record-inner-integration')
        receipt = self.call(*args, body=payload)
        self.rev = receipt['revision']
        self.assertEqual(receipt['charged_inner_attempt'], 1)
        self.assertEqual(receipt['integration_commits'], [payload['checkpoint']])
        self.assertTrue(self.call(*args, body=payload)['replayed'])
        self.lifecycle('record-inner-integration', payload, valid=False)
        view = self.call('status', self.state)
        self.assertEqual((view['status'], view['inner_attempt'], view['pending_inner_attempt']), ('hold', 1, None))

    def test_no_change_interruption_ignores_other_commits_but_requires_clean_source(self):
        self.start_implementation()
        dirty = self.root / 'src/unintegrated.py'
        dirty.write_text('scratch\n')
        self.lifecycle('begin-inner-attempt', valid=False)
        dirty.unlink()
        started = self.lifecycle('begin-inner-attempt')
        dirty.write_text('scratch\n')
        self.lifecycle('record-no-change-interruption', self.settle_payload(started), valid=False)
        dirty.unlink()
        revision = self.brief(mode='write', base=started['base_revision'])
        self.apply('reserve', {'id': 'T-A', 'revision_id': revision, 'workspace': str(self.root), 'profile_ref': 'fixture'})
        self.lifecycle('record-no-change-interruption', self.settle_payload(started), valid=False)
        self.apply('prove-non-dispatch', {'id': 'T-A', 'evidence': 'fixture: reservation was never submitted'})
        (self.root / 'notes.md').write_text('recovery notes\n')
        self.git('add', 'notes.md')
        self.git('commit', '-qm', 'record interruption notes')
        payload = self.settle_payload(started)
        receipt = self.lifecycle('record-no-change-interruption', payload)
        self.assertNotIn('charged_inner_attempt', receipt)
        self.assertEqual(receipt['integration_commits'], [])
        self.assertEqual(self.call('status', self.state)['inner_attempt'], 0)
        retry = self.lifecycle('begin-inner-attempt')
        self.lifecycle('record-no-change-interruption', payload, valid=False)
        self.lifecycle('record-no-change-interruption', self.settle_payload(retry))

    def test_integrated_change_and_revert_is_not_a_no_change_interruption(self):
        self.start_implementation()
        started = self.lifecycle('begin-inner-attempt')
        branch = self.git('symbolic-ref', '--short', 'HEAD')
        self.git('switch', '-qc', 'worker')
        self.commit_implementation('method that was replaced\n')
        worker_result = self.settle_payload(started)
        self.git('switch', '-q', branch)
        self.lifecycle('record-inner-integration', worker_result, valid=False)
        self.git('merge', '-q', '--no-ff', 'worker', '-m', 'integrated worker branch')
        change = self.git('rev-parse', 'HEAD')
        self.git('revert', '-m', '1', '--no-edit', change)
        payload = self.settle_payload(started)
        self.lifecycle('record-no-change-interruption', payload, valid=False)
        charged = self.lifecycle('record-inner-integration', payload)
        self.assertEqual(charged['integration_commits'], [change, payload['checkpoint']])

    def test_inner_attempt_cap_applies_before_new_work(self):
        self.start_implementation()
        for i in range(3):
            self.integrate_attempt(f'method version {i}\n')
        self.lifecycle('begin-inner-attempt', valid=False)
        view = self.call('status', self.state)
        self.assertEqual((view['inner_attempt'], view['pending_inner_attempt']), (3, None))

    def test_readiness_requires_approved_protocol_and_observed_required_tests(self):
        self.start_implementation()
        for name, changes in [('wrong-protocol', {'protocol_review': 'another-review'}),
                              ('wrong-tests', {'tests': {'smoke': {'exit_code': 0, 'output': 'artifact.txt'}}}),
                              ('failed-test', {'tests': {'unit': {'exit_code': 1, 'output': 'artifact.txt'}}})]:
            info = self.readiness_manifest(name)['readiness'] | changes
            result = self.review('readiness', name, extra={'readiness': info}, route=None)
            self.assertEqual(result['verdict'], 'none')
            self.assertEqual(self.call('status', self.state)['status'], 'active')
            self.resolve_gate_hold(name, 'fixture: corrected submission')
        # The bounded no-verdict limit is not expanded by bad readiness evidence.
        self.review('readiness', 'exhausted', valid=False)

    def test_readiness_reuse_requires_exact_diff_checks_and_unchanged_assumptions_evidence(self):
        self.start_implementation()
        self.review('readiness', 'ready')
        original = self.get('ready')['manifest']
        self.lifecycle('return-to-implementation', {'reason': 'in-plan implementation fix', 'artifacts': self.hashes})
        self.integrate_attempt('fixed implementation\n')
        self.review('complete', 'not-ready', valid=False)
        candidate = self.readiness_manifest('reused')
        candidate['artifacts'].update({p: h for p, h in original['artifacts'].items() if p != 'src/method.py'})
        before, after = original['readiness']['revision'], candidate['readiness']['revision']
        diff = self.root / 'change.patch'
        diff.write_bytes(source_diff(self.root, before, after))
        candidate['artifacts'][diff.name] = hashlib.sha256(diff.read_bytes()).hexdigest()
        unchanged = dict.fromkeys(('interfaces', 'contracts', 'validity_assumptions'), 'artifact.txt')
        proof = {'diff': diff.name, 'unchanged': unchanged}
        params = {'review_id': 'ready', 'manifest': candidate, 'proof': proof}
        self.lifecycle('reuse-readiness', {**params, 'proof': {'diff': diff.name}}, valid=False)
        self.lifecycle('reuse-readiness', {**params, 'proof': {**proof, 'diff': 'artifact.txt'}}, valid=False)
        candidate['artifacts']['different-data.md'] = self.fixture_file('different-data.md', 'changed dataset contents')
        rebound = {**candidate, 'artifact_roles': {**candidate['artifact_roles'], 'dataset-manifest': 'different-data.md'}}
        failure = self.lifecycle('reuse-readiness', {**params, 'manifest': rebound}, valid=False)
        self.assertIn('reviewed package roles', failure['refused'])
        self.lifecycle('reuse-readiness', params)
        self.assertEqual(self.call('status', self.state)['gate_flags'], [])
        self.assertEqual(self.get('ready')['manifest'], original)  # Reuse does not forge a new Advisor verdict.
        (self.root / 'reused-tests.log').write_text('changed test output\n')
        self.review('complete', 'stale-reuse', valid=False)
        self.lifecycle('return-to-implementation', {'reason': 'readiness evidence drift', 'artifacts': self.hashes})
        self.review('readiness', 'fresh-readiness')
        self.review('complete', 'after-fresh-review')

    def test_readiness_is_stale_if_other_source_files_change(self):
        self.start_implementation()
        self.review('readiness', 'ready', route=None)
        added = self.root / 'src/new_component.py'
        added.write_text('new source not named in the manifest\n')
        self.git('add', 'src')
        self.git('commit', '-qm', 'uncaptured change')
        self.lifecycle('gate-route', {'id': 'ready', 'route': 'continue'}, valid=False)
        self.assertTrue(any(flag['review_id'] == 'ready' for flag in self.call('status', self.state)['gate_flags']))
        self.lifecycle('withdraw-stale-review', {'id': 'ready'})

    def test_required_okf_result_is_checked_and_pinned_to_the_review_target(self):
        self.open_cycle('1', initial=True)
        manifest = self.gate_manifest('cycle', 'precheck')
        request = self.begin_okf('index.md', 'director-brief.md')
        staged = self.stage_director_documents(request)
        self.prepare_okf(request, **staged, writer_bytes=b'{', valid=False)
        self.prepare_okf(request, **staged)
        publication = self.publish_okf(request)
        self.check_okf({**manifest, 'okf_reader_required': True}, publication=publication, valid=False)
        result = self.review('cycle', 'missing-check', route=None, check_okf=False)
        self.assertEqual(result['verdict'], 'none')
        self.assertEqual(self.call('status', self.state)['status'], 'active')
        self.resolve_gate_hold('missing-check', 'fixture: fresh valid OKF evidence')
        self.review('cycle', 'ready-check', route=None)
        check = self.get('ready-check')['okf_check']
        other = self.check_okf(manifest, publication=self.get(self.get(check)['publication_id']))['op_id']
        self.assertNotEqual(check, other)
        self.lifecycle('gate-route', {'id': 'ready-check', 'route': 'hold', 'reason': 'fixture', 'okf_check': other},
                       valid=False)
        self.lifecycle('gate-route', {'id': 'ready-check', 'route': 'hold', 'reason': 'fixture'})

    def test_required_reader_must_be_sufficient_nonempty_and_snapshot_bound(self):
        self.open_cycle('reader-evidence', initial=True)
        manifest = self.gate_manifest('cycle', 'reader-evidence') | {'okf_reader_required': True}
        partial = self.check_okf(manifest, reader_status='partial', valid=False)
        self.assertIn('sufficient primary evidence', partial['refused'])
        empty = self.check_okf(manifest, reader_status='sufficient', reader_evidence=False, valid=False)
        self.assertIn('sufficient primary evidence', empty['refused'])
        stale = self.check_okf(manifest, reader_status='sufficient', reader_snapshot=False, valid=False)
        self.assertIn('different or unspecified hub snapshot', stale['refused'])
        accepted = self.check_okf(manifest, reader_status='sufficient')
        self.assertTrue(accepted['launch_eligible'] is False)
        self.assertTrue(self.get(accepted['op_id'])['reader_checked'])

    def test_mutated_reader_result_invalidates_cycle_gate_receipt(self):
        self.open_cycle('reader-stale', initial=True)
        self.review('cycle', 'reader-review', route=None, extra={'okf_reader_required': True})
        check = self.get('reader-review')['okf_check']
        receipt = self.get(check)
        publication = self.get(receipt['publication_id'])
        reader = next(path for path in receipt['service_artifacts'] if path != publication['writer_result'])
        result = self.root / reader
        before = result.read_bytes()
        result.write_bytes(before + b' ')
        rejected = self.lifecycle('gate-route', {'id': 'reader-review', 'route': 'hold', 'reason': 'fixture'}, valid=False)
        self.assertIn('artifact drift', rejected['refused'])
        result.write_bytes(before)

    def test_changed_okf_hub_and_service_result_require_a_fresh_gate_check(self):
        self.open_cycle('1', initial=True)
        self.review('cycle', 'cycle-review', route=None)
        request = self.begin_okf('note.md')
        (self.root / request['staging'] / 'note.md').write_text('---\ntype: Note\n---\nNew hub observation.\n')
        self.prepare_okf(request, updated=['note.md'])
        publication = self.publish_okf(request)
        params = {'id': 'cycle-review', 'route': 'hold', 'reason': 'fixture'}
        self.lifecycle('gate-route', params, valid=False)
        manifest = self.get('cycle-review')['manifest']
        check = self.check_okf(manifest, publication=publication)['op_id']
        writer = self.root / publication['writer_result']
        content = writer.read_bytes()
        writer.write_text('{\"stale\":true}')
        self.lifecycle('gate-route', {**params, 'okf_check': check}, valid=False)
        writer.write_bytes(content)
        refreshed = self.check_okf(manifest, publication=publication)['op_id']
        self.lifecycle('gate-route', {**params, 'okf_check': refreshed})
        routed = self.get('cycle-review')['routed_okf_check']
        self.assertNotEqual(routed, refreshed)  # The resolved decision adds machine JSON to the verified hub.
        self.assertEqual(self.get(routed)['checked_manifest'], self.get(refreshed)['checked_manifest'])

    def test_okf_only_one_pending_request_and_abort_never_lifts_hold(self):
        self.seed_okf()
        body = {'paths': ['note.md'], 'request_artifacts': self.hashes}
        args = [self.args('lifecycle', 'begin-okf-publication') for _ in range(2)]
        with ThreadPoolExecutor(2) as workers:
            results = list(workers.map(lambda argv: self.raw(*argv, body=body), args))
        self.assertEqual(sorted(code for code, _ in results), [0, 1])
        start = next(receipt for code, receipt in results if code == 0)
        self.rev = start['revision']
        self.assertFalse(start['launch_eligible'])
        self.lifecycle('begin-okf-publication', body, valid=False)  # Even with the new ledger revision.
        self.lifecycle('publish-okf', {'request_id': start['op_id']}, valid=False)
        self.lifecycle('open-hold', {'reason': 'interrupted before staging'})
        self.assertEqual(self.call('next', self.state)['candidates'][0]['request_id'], start['op_id'])
        abort = {'request_id': start['op_id'], 'writer_state': 'not-dispatched', 'recovery_artifacts': self.hashes}
        self.lifecycle('abort-okf-publication', {**abort, 'request_id': 'other'}, valid=False)
        self.lifecycle('abort-okf-publication', {**abort, 'writer_state': 'timed-out'}, valid=False)
        self.lifecycle('abort-okf-publication', abort)
        status = self.call('status', self.state)
        self.assertIsNone(status['okf_publication']['pending'])
        self.assertEqual(status['status'], 'hold')

    def test_okf_refuses_unscoped_stage_and_no_op_cannot_bless_unmanaged_markdown(self):
        hub = self.seed_okf()
        request = self.begin_okf('note.md')
        stage = self.root / request['staging']
        (stage / 'state.json').write_text('{}\n')
        self.prepare_okf(request, valid=False)
        (stage / 'state.json').unlink()
        (stage / 'escape').symlink_to(hub, target_is_directory=True)
        self.prepare_okf(request, valid=False)
        (stage / 'escape').unlink()
        self.prepare_okf(request, updated=['note.md'], valid=False)  # No diff, so the envelope is inaccurate.
        before = hub_fingerprint(self.root)
        review_needed = {'status': 'needs_review', 'created': [], 'updated': [], 'deprecated': [],
                         'evidence': ['fixture ambiguity'], 'validation': [], 'warnings': [],
                         'revision': {'state': 'staged only', 'git_commit_made': False}}
        self.prepare_okf(request, writer_bytes=json.dumps(review_needed).encode(), valid=False)
        self.assertEqual(before, hub_fingerprint(self.root))
        self.prepare_okf(request)
        self.publish_okf(request)
        (hub / 'note.md').write_text('unmanaged edit\n')
        self.lifecycle('begin-okf-publication', {'paths': [], 'request_artifacts': self.hashes}, valid=False)

    def test_okf_publish_creates_only_valid_indexed_concepts_and_checkpoints_new_dirs(self):
        request = self.begin_okf('reports/summary.md', 'index.md')
        stage = self.root / request['staging']
        (stage / 'reports').mkdir()
        (stage / 'reports/summary.md').write_text('---\ntype: Note\n---\nFixture summary.\n')
        self.prepare_okf(request, created=['reports/summary.md'], valid=False)
        with (stage / 'index.md').open('a') as index:
            index.write('- [Summary](reports/summary.md)\n')
        self.prepare_okf(request, created=['reports/summary.md'], updated=['index.md'])
        published = self.publish_okf(request)
        self.assertEqual(published['hub_sha256'], hub_fingerprint(self.root))
        self.assertEqual((self.root / HUB / 'reports/summary.md').read_bytes(), (stage / 'reports/summary.md').read_bytes())

    def test_interrupted_okf_publish_keeps_intent_and_blocks_gate_until_recovered(self):
        self.open_cycle('1', initial=True)
        self.review('cycle', 'pending-route', route=None)
        hub = self.root / HUB
        index, note = hub / 'index.md', hub / 'note.md'
        old_note = note.read_bytes()
        request = self.begin_okf('index.md', 'note.md')
        stage = self.root / request['staging']
        (stage / 'index.md').write_bytes(index.read_bytes() + b'\nNew publication.\n')
        (stage / 'note.md').write_bytes(old_note + b'\nNew record.\n')
        prepared = self.prepare_okf(request, updated=['index.md', 'note.md'])
        args = self.args('lifecycle', 'publish-okf')
        payload = {'request_id': request['op_id']}
        # Terminate the real ledger process after the first replacement but before
        # the ledger is saved. Separate invocations must see the persistent intent.
        proc = subprocess.run([sys.executable, '-B', '-c', '''
import os, sys
sys.path.insert(0, sys.argv.pop(1))
import hub_publication, ledger
replace = hub_publication.replace_file
def crash(*args):
    replace(*args)
    os._exit(91)
hub_publication.replace_file = crash
sys.exit(ledger.main())
''', str(HERE), *args], input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(proc.returncode, 91, proc.stdout + proc.stderr)
        self.assertEqual(index.read_bytes(), (stage / 'index.md').read_bytes())
        self.assertEqual(note.read_bytes(), old_note)
        status = self.call('status', self.state)
        self.assertEqual(status['meta']['revision'], self.rev)
        self.assertEqual(status['okf_publication']['pending']['prepare_id'], prepared['op_id'])
        route = {'id': 'pending-route', 'route': 'hold', 'reason': 'fixture'}
        self.lifecycle('gate-route', route, valid=False)
        self.lifecycle('abort-okf-publication', payload | {'writer_state': 'terminated', 'recovery_artifacts': self.hashes}, valid=False)
        note.write_text('unexpected bytes\n')
        self.call(*args, body=payload, valid=False)
        self.assertEqual(note.read_text(), 'unexpected bytes\n')
        note.write_bytes(old_note)
        staged_note = (stage / 'note.md').read_bytes()
        (stage / 'note.md').write_bytes(old_note + b'Not the prepared target.\n')
        self.call(*args, body=payload, valid=False)
        self.assertEqual(note.read_bytes(), old_note)
        (stage / 'note.md').write_bytes(staged_note)
        published = self.call(*args, body=payload)
        self.rev = published['revision']
        self.assertTrue(self.call(*args, body=payload)['replayed'])
        self.assertEqual(note.read_bytes(), staged_note)
        self.assertIsNone(self.call('status', self.state)['okf_publication']['pending'])
        self.lifecycle('gate-route', route, valid=False)  # Must check the new hub checkpoint.
        fresh = self.check_okf(self.get('pending-route')['manifest'], publication=published)
        self.lifecycle('gate-route', route | {'okf_check': fresh['op_id']})

    def test_initial_cycle_is_charged_only_when_planning_starts(self):
        view = self.call('status', self.state)
        self.assertEqual((view['stage'], view['cycles_used'], view['cycles_remaining']), ('CREATED', 0, 3))
        payload = {'charter_ref': 'charter.md'}
        self.lifecycle('start-planning', payload, valid=False)
        self.lifecycle('start-scoping')
        self.lifecycle('start-planning', valid=False)
        view = self.call('status', self.state)
        self.assertEqual((view['stage'], view['cycles_used'], view['cycles_remaining']), ('SCOPING', 0, 3))

        args, payload = self.route_commit(self.args('lifecycle', 'start-planning'), payload)
        receipt = self.call(*args, body=payload)
        self.rev = receipt['revision']
        self.assertEqual(receipt['charged_cycle'], 1)
        replay = self.call(*args, body=payload)
        self.assertTrue(replay['replayed'])
        self.assertEqual(replay['revision'], self.rev)
        self.lifecycle('start-planning', payload, valid=False)
        view = self.call('status', self.state)
        self.assertEqual((view['stage'], view['outer_cycle'], view['cycles_used'], view['cycles_remaining']),
                         ('PLANNING', 1, 1, 2))
        self.review('protocol', 'blocked-protocol', verdict='block', route=None)
        self.assertEqual(self.call('status', self.state)['cycles_used'], 1)

    def test_previously_initialized_cycle_is_not_charged_again(self):
        snapshot = json.loads(self.state.read_text())
        snapshot['budgets']['outer_cycles']['used'] = 1  # A managed snapshot produced before this change.
        self.state.write_text(json.dumps(snapshot))
        self.lifecycle('start-scoping')
        receipt = self.lifecycle('start-planning', {'charter_ref': 'charter.md'})
        self.assertNotIn('charged_cycle', receipt)
        self.assertEqual(self.call('status', self.state)['cycles_used'], 1)

    def test_cycle_charges_once_and_reports_on_last_cycle(self):
        for cycle in range(1, 4):
            self.open_cycle(str(cycle), initial=cycle == 1)
            self.lifecycle('progress', {'verdict': 'advanced', 'credible_lever': True, 'evidence_refs': ['artifact.txt']})
            if cycle < 3:
                self.review('cycle', f'cycle-{cycle}', route=None,
                            extra={'proposed_route': 'replan', 'next_plan': f'v{cycle + 1}', 'replan_rationale': 'new lever'})
                payload = {'id': f'cycle-{cycle}', 'route': 'replan'}
                args, payload = self.route_commit(self.args('lifecycle', 'gate-route'), payload)
                out = self.call(*args, body=payload)
                self.rev = out['revision']
                selected = json.loads(self.git('show', f"{out['checkpoint']}:{out['decision_path']}"))
                self.assertEqual((selected['selected_route'], selected['resulting_cycle'], selected['charged_cycles']),
                                 ('replan', cycle + 1, 1))
                self.assertEqual(selected['manifest_id'], f'cycle-{cycle}@v1')
                self.assertTrue(self.call(*args, body=payload)['replayed'])
                self.lifecycle('gate-route', payload, valid=False)
            else:
                self.lifecycle('objective', {'id': 'O-1', 'status': 'met', 'evidence_refs': ['artifact.txt']})
                self.review('cycle', 'cycle-final', route='report')
        self.review('report', 'final-report', route='complete')
        view = self.call('status', self.state)
        self.assertEqual((view['outer_cycle'], view['cycles_used'], view['stage']), (3, 3, 'COMPLETED'))

    def test_plan_change_draft_does_not_charge_and_approved_replan_charges_once(self):
        self.open_cycle('draft', initial=True)
        self.lifecycle('progress', {'verdict': 'marginal', 'credible_lever': True, 'evidence_refs': ['artifact.txt']})
        before = self.call('status', self.state)
        self.review('cycle', 'draft-revision', verdict='revise', route='remediate-plan')
        mid = self.call('status', self.state)
        self.assertEqual((mid['outer_cycle'], mid['cycles_used'], mid['stage']), (before['outer_cycle'], before['cycles_used'], 'ANALYZING'))
        self.review('cycle', 'draft-approval', extra={'proposed_route': 'replan', 'next_plan': 'v2',
                                                       'replan_rationale': 'fixture plan repair'}, route='replan')
        after = self.call('status', self.state)
        self.assertEqual((after['outer_cycle'], after['cycles_used'], after['stage']), (2, before['cycles_used'] + 1, 'PLANNING'))

    def test_untagged_director_message_is_refused_and_fyi_never_holds(self):
        untagged = {'id': 'UNTAGGED', 'delivery': 'sent', 'artifacts': self.hashes, 'summary': 'missing tag',
                    'next_step': 'Lead asks for a tag'}
        self.lifecycle(director.MESSAGE, untagged, valid=False)
        self.lifecycle(director.MESSAGE, {'id': 'F-NOHOLD', 'tag': 'FYI', 'summary': 'Fixture FYI',
                       'next_step': 'Lead continues', 'delivery': 'sent', 'artifacts': self.hashes})
        self.assertEqual(self.call('status', self.state)['status'], 'active')
        self.assertEqual(self.get('F-NOHOLD')['status'], 'closed')

    def test_wrong_assignment_or_revision_ids_cannot_complete(self):
        revision = self.brief('ids')
        self.apply('reserve', {'id': 'T-ids', 'revision_id': revision, 'profile_ref': 'fixture'})
        self.apply('attach-run', {'id': 'T-ids', 'run_id': 'run-ids', 'evidence': 'fixture launch'})
        self.apply('observe-termination', {'id': 'T-ids', 'evidence': 'fixture exit'})
        bad = {'id': 'S-wrong', 'assignment_id': 'A-other', 'revision_id': revision, 'attempt_id': 'T-ids',
               'status': 'SUCCESS', 'deliverable': 'artifact.txt', 'evidence_refs': ['artifact.txt'], 'gaps': [],
               'source_versions': {'input': 'v1'}}
        self.apply('result', bad, valid=False)
        bad = {**bad, 'assignment_id': 'A-ids', 'revision_id': 'R-other'}
        self.apply('result', bad, valid=False)

    def resolve_gate_hold(self, key, resolution='fixture triage complete', artifacts=None):
        return self.lifecycle('resolve-gate-hold', {'id': key, 'resolution': resolution,
                                                    'artifacts': artifacts or self.hashes})

    def begin_early_stagnation(self, slug):
        self.open_cycle(f'{slug}-1', initial=True)
        self.lifecycle('progress', {'verdict': 'stalled', 'credible_lever': False, 'evidence_refs': ['artifact.txt']})
        self.review('cycle', f'{slug}-replan', route='replan', extra={'proposed_route': 'replan', 'next_plan': 'v2',
                                                    'replan_rationale': 'fixture alternate lever'})
        self.open_cycle(f'{slug}-2')
        self.lifecycle('progress', {'verdict': 'regressed', 'credible_lever': False, 'evidence_refs': ['artifact.txt']})
        self.assertTrue(self.call('termination-check', self.state)['predicates']['early_stagnation'])

    def test_early_stagnation_requires_stop_unless_achievement_is_reportable(self):
        self.begin_early_stagnation('stop')
        self.review('cycle', 'stagnation-stop', route=None, extra={'proposed_route': 'stop'})
        report = 'reports/stagnation-status.md'
        self.fixture_file(report, 'Fixture status: evidence remains incomplete.\\n')
        args, payload = self.route_commit(self.args('lifecycle', 'gate-route'),
                                         {'id': 'stagnation-stop', 'route': 'stop', 'status_report': report})
        stopped = self.call(*args, body=payload)
        self.rev = stopped['revision']
        status = self.call('status', self.state)
        self.assertEqual((status['status'], status['stage'], status['cycles_used']), ('suspended', 'ANALYZING', 2))


    def test_early_stagnation_with_achievement_still_routes_to_report(self):
        self.begin_early_stagnation('achieve')
        self.lifecycle('objective', {'id': 'O-1', 'status': 'met', 'evidence_refs': ['artifact.txt']})
        self.review('cycle', 'stagnation-achievement', extra={'proposed_route': 'report'}, route='report')
        self.assertEqual(self.call('status', self.state)['stage'], 'REPORTING')
        self.assertEqual(self.call('status', self.state)['status'], 'active')

    def test_inconclusive_cycle_gets_one_evidence_recheck_then_stays_held(self):
        self.open_cycle('inconclusive', initial=True)
        self.lifecycle('progress', {'verdict': 'marginal', 'credible_lever': True, 'evidence_refs': ['artifact.txt']})
        self.review('cycle', 'inconclusive-one', verdict='inconclusive', route='gather-evidence')
        self.review('cycle', 'inconclusive-two', verdict='inconclusive', route=None)
        args, payload = self.route_commit(self.args('lifecycle', 'gate-route'),
                                         {'id': 'inconclusive-two', 'route': 'hold', 'reason': 'second review unresolved'})
        self.call(*args, body=payload)
        self.rev = json.loads(self.state.read_text())['revision']
        self.assertEqual(self.call('status', self.state)['status'], 'active')
        self.resolve_gate_hold('inconclusive-two', 'evidence retry exhausted')
        retry = self.review('cycle', 'inconclusive-three', verdict='inconclusive', route=None, valid=False)
        self.assertIn('bounded inconclusive re-review exhausted', retry['refused'])

    def test_replan_saved_before_lost_ack_replays_without_double_charge(self):
        self.open_cycle('lost-ack', initial=True)
        self.lifecycle('progress', {'verdict': 'advanced', 'credible_lever': True, 'evidence_refs': ['artifact.txt']})
        self.review('cycle', 'lost-ack-review', route=None,
                    extra={'proposed_route': 'replan', 'next_plan': 'v2', 'replan_rationale': 'fixture cycle repair'})
        args, payload = self.route_commit(self.args('lifecycle', 'gate-route'),
                                         {'id': 'lost-ack-review', 'route': 'replan'})
        proc = subprocess.run([sys.executable, '-B', '-c', '''
import builtins, os, sys
sys.path.insert(0, sys.argv.pop(1))
builtins.print = lambda *args, **kwargs: os._exit(91)
import ledger
sys.exit(ledger.main())
''', str(HERE), *args], input=json.dumps(payload), capture_output=True, text=True, timeout=15)
        self.assertEqual(proc.returncode, 91, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, '')
        saved = json.loads(self.state.read_text())
        self.rev = saved['revision']
        self.assertEqual((saved['lifecycle']['stage'], saved['lifecycle']['outer_cycle'],
                          saved['budgets']['outer_cycles']['used']), ('PLANNING', 2, 2))
        receipt = saved['operations'][args[args.index('--op-id') + 1]]
        self.assertEqual((receipt['selected_route'], receipt['resulting_cycle'], receipt['charged_cycles']),
                         ('replan', 2, 1))
        replay = self.call(*args, body=payload)
        self.assertTrue(replay['replayed'])
        reread = json.loads(self.state.read_text())
        self.assertEqual((reread['revision'], reread['budgets']['outer_cycles']['used']), (self.rev, 2))

    def director_ask(self, key, *, scope=None, trigger='authority', delivery='sent'):
        return {'id': key, 'tag': 'DECISION-REQUIRED', 'scope': scope or {'kind': 'project'}, 'trigger': trigger,
                'ask': 'May we narrow the affected work?', 'why_now': 'Fixture authority boundary',
                'options': {'narrow': {'outcome': 'narrow', 'consequence': 'defer the excluded work'}},
                'recommendation': {'option': 'narrow', 'basis': 'fits existing cap', 'change_if': 'new evidence'},
                'without_reply': 'affected work remains parked', 'delivery': delivery, 'artifacts': self.hashes}

    def director_reply(self, key, *, option='narrow', valid=True):
        return self.lifecycle(director.REPLY, {'id': key, 'classification': 'authorization', 'option': option,
                              'readback': 'Fixture readback of the permitted effect', 'artifacts': self.hashes}, valid=valid)

    def test_director_scope_fyi_and_ambiguous_reply_do_not_release_or_overblock(self):
        self.lifecycle(director.MESSAGE, {'id': 'F-1', 'tag': 'FYI', 'summary': 'Fixture optional failure',
                       'next_step': 'Lead will reconcile', 'delivery': 'sent', 'artifacts': self.hashes})
        first = self.apply('assess-task', self.assessment('A'))['op_id']
        self.call('check-task', self.state, first)
        request = self.director_ask('D-1', scope={'kind': 'tasks', 'task_ids': ['pilot-A']}, delivery='pending')
        self.lifecycle(director.MESSAGE, request)
        self.call('check-task', self.state, first, valid=False)
        payload = self.brief_payload('A') | {'assessment_id': first}
        self.apply('issue', payload, valid=False)
        self.brief('B')  # A's authority issue does not prevent independent dispatch preparation.
        self.assertEqual(self.call('status', self.state)['status'], 'active')
        self.director_reply('D-1', valid=False)  # No observed delivery.
        self.lifecycle(director.DELIVERY, {'id': 'D-1', 'status': 'sent', 'artifacts': self.hashes})
        self.lifecycle(director.REPLY, {'id': 'D-1', 'classification': 'ambiguous',
                       'next_step': 'Which option did you mean?', 'artifacts': self.hashes})
        self.assertEqual(self.get('D-1')['status'], 'open')
        published = self.publish_director('D-1')
        self.lifecycle(director.FILE, {'id': 'D-1', 'publication_id': published})
        self.call('check-task', self.state, first, valid=False)
        self.director_reply('D-1')
        self.lifecycle(director.FILE, {'id': 'D-1', 'publication_id': published}, valid=False)
        unindexed = self.publish_director('D-1', index_decisions=False)
        bad = self.lifecycle(director.FILE, {'id': 'D-1', 'publication_id': unindexed}, valid=False)
        self.assertIn('root index', bad['refused'])
        current = self.publish_director('D-1')
        self.lifecycle(director.FILE, {'id': 'D-1', 'publication_id': current})
        self.assertEqual(self.get('D-1')['status'], 'closed')
        self.apply('issue', payload, valid=False)  # Old READY predates the authorized scope.
        renewed = self.apply('assess-task', self.assessment('A'))['op_id']
        self.apply('issue', {**payload, 'assessment_id': renewed})
        (self.root / HUB / 'decisions/D-1.md').write_text('unexpected replacement')
        self.call('check-task', self.state, renewed, valid=False)

    def test_project_resource_hold_requires_reconciled_filed_authority(self):
        req = self.director_ask('RES-1', trigger='resources')
        self.lifecycle(director.MESSAGE, req)
        self.assertEqual(self.call('status', self.state)['status'], 'hold')
        self.lifecycle('begin-okf-publication', {'paths': ['unrelated.md'], 'request_artifacts': self.hashes}, valid=False)
        self.lifecycle(director.MESSAGE, {**req, 'id': 'RES-2', 'supersedes': 'RES-1', 'trigger': 'authority'}, valid=False)
        self.lifecycle(director.MESSAGE, {**req, 'id': 'RES-2', 'supersedes': 'RES-1'})
        self.assertEqual(self.get('RES-1')['status'], 'superseded')
        self.lifecycle('resolve-hold', {'resolution': 'assumed approval'}, valid=False)
        self.director_reply('RES-2')
        self.lifecycle('resolve-hold', {'resolution': 'reply not filed'}, valid=False)
        publication = self.publish_director('RES-1', 'RES-2')
        self.lifecycle(director.FILE, {'id': 'RES-2', 'publication_id': publication}, valid=False)
        self.lifecycle(director.FILE, {'id': 'RES-1', 'publication_id': publication})
        self.lifecycle(director.FILE, {'id': 'RES-2', 'publication_id': publication})
        self.lifecycle('resolve-hold', {'resolution': 'no proof of narrowing'}, valid=False)
        closed = self.lifecycle('resolve-hold', {'resolution': 'narrowing reconciled',
                                'resource_decisions': ['RES-2'], 'reconciliation_artifacts': self.hashes})
        self.assertEqual(closed['director_resume_ids'], ['RES-2'])
        self.assertEqual(self.call('status', self.state)['status'], 'active')

    def test_director_stop_parks_immediately_and_does_not_assert_child_exit(self):
        revision_id = self.brief('stop')
        self.apply('reserve', {'id': 'running', 'revision_id': revision_id, 'profile_ref': 'fixture'})
        self.apply('attach-run', {'id': 'running', 'run_id': 'run-stop', 'evidence': 'fixture dispatch'})
        self.lifecycle(director.STOP, {'id': 'STOP-1', 'reason': 'Fixture urgent stop; hub not available yet'})
        view = self.call('status', self.state)
        self.assertEqual(view['status'], 'hold')
        self.assertEqual(view['director']['unresolved']['assignments'], ['running'])
        self.assertNotIn('stop_reconciled', self.get('STOP-1'))
        status_file = {'status_report': 'artifact.txt', 'artifacts': self.hashes, 'director_decision': 'STOP-1'}
        self.lifecycle('suspend-held', status_file, valid=False)
        self.director_reply('STOP-1', option='stop')
        pub = self.publish_director('STOP-1')
        self.lifecycle(director.FILE, {'id': 'STOP-1', 'publication_id': pub})
        self.lifecycle('resolve-hold', {'resolution': 'must remain stopped'}, valid=False)
        proof = {'id': 'STOP-1', 'summary': 'Fixture exit and effects checked', 'artifacts': self.hashes}
        failure = self.lifecycle(director.STOPPED, proof, valid=False)
        self.assertIn('still unresolved', failure['refused'])
        suspended = self.lifecycle('suspend-held', status_file)
        self.assertIsNone(suspended['stop_reconciled'])
        self.apply('observe-termination', {'id': 'running', 'evidence': 'fixture process exit confirmed'})
        observed = self.lifecycle(director.STOPPED, proof)
        self.assertEqual(self.get('STOP-1')['stop_reconciled'], observed['op_id'])
        update = self.publish_director('STOP-1')
        self.lifecycle(director.FILE, {'id': 'STOP-1', 'publication_id': update})
        self.assertEqual(self.call('status', self.state)['status'], 'suspended')

    def test_pending_director_authority_blocks_gate_and_filing_requires_a_fresh_review(self):
        self.lifecycle('start-scoping')
        self.lifecycle('start-planning', {'charter_ref': 'charter.md'})
        self.review('protocol', 'before-authority', route=None)
        self.lifecycle(director.MESSAGE, self.director_ask('D-GATE', scope={'kind': 'tasks', 'task_ids': ['pilot-A']}))
        proposed = {'id': 'before-authority', 'route': 'continue'}
        refused = self.lifecycle('gate-route', proposed, valid=False)
        self.assertIn('D-GATE blocks', refused['refused'])
        self.director_reply('D-GATE')
        publication = self.publish_director('D-GATE')
        self.lifecycle(director.FILE, {'id': 'D-GATE', 'publication_id': publication})
        refused = self.lifecycle('gate-route', proposed, valid=False)
        self.assertIn('gate input state changed', refused['refused'])
        self.lifecycle('withdraw-stale-review', {'id': 'before-authority'})
        self.review('protocol', 'now-current')

    def test_stale_standing_brief_cannot_pass_cycle_precheck(self):
        self.open_cycle('brief', initial=True)
        manifest = self.gate_manifest('cycle', 'brief-test')
        checked = self.check_okf(manifest)
        publication = self.get(checked['publication_id'])
        self.lifecycle(director.MESSAGE, {'id': 'F-brief', 'tag': 'FYI', 'summary': 'New material event',
                       'next_step': 'refresh brief', 'delivery': 'sent', 'artifacts': self.hashes})
        failure = self.check_okf(manifest, publication=publication, valid=False)
        self.assertIn('standing Director brief is stale', failure['refused'])
        self.check_okf(manifest)

    def test_gate_checkpoint_refuses_uncommitted_ledger_and_role_file(self):
        self.lifecycle('start-scoping')
        self.lifecycle('start-planning', {'charter_ref': 'charter.md'})
        self.review('protocol', 'checkpoint-review', route=None)
        payload = {'id': 'checkpoint-review', 'route': 'continue'}
        args = self.args('lifecycle', 'gate-route')
        op = args[args.index('--op-id') + 1]
        preview = self.call('checkpoint-plan', self.state, 'gate-route', '--op-id', op, '--input', '-', body=payload)
        self.assertEqual(preview['decision']['selected_route'], 'continue')
        self.assertFalse((self.root / preview['decision_path']).exists())
        with_missing = self.get('checkpoint-review')['manifest']['artifact_roles']['hypotheses']
        args, payload = self.route_commit(args, payload, omit=[with_missing])
        failure = self.call(*args, body=payload, valid=False)
        self.assertIn(with_missing, failure['refused'])
        self.lifecycle('objective', {'id': 'O-1', 'status': 'partial', 'evidence_refs': ['artifact.txt']})
        self.git('add', '--', with_missing)
        self.git('commit', '-qm', preview['git_subject'])
        body = {**payload, 'checkpoint': self.git('rev-parse', 'HEAD')}
        args = args[:-1] + (str(self.rev),)
        failure = self.call(*args, body=body, valid=False)
        self.assertIn('exact bytes: project-state.json', failure['refused'])
        self.git('add', '--', self.state.name)
        self.git('commit', '-qm', preview['git_subject'])
        body['checkpoint'] = self.git('rev-parse', 'HEAD')
        self.call(*args, body=body)

    def test_gate_refuses_contradictory_decision_and_rewritten_checkpoint_lineage(self):
        self.lifecycle('start-scoping')
        self.lifecycle('start-planning', {'charter_ref': 'charter.md'})
        self.review('protocol', 'route-identity', route=None)
        args = self.args('lifecycle', 'gate-route')
        args, payload = self.route_commit(args, {'id': 'route-identity', 'route': 'continue'})
        op = args[args.index('--op-id') + 1]
        preview = self.call('checkpoint-plan', self.state, 'gate-route', '--op-id', op, '--input', '-', body=payload)
        path = preview['decision_path']
        self.fixture_file(path, preview['decision'] | {'selected_route': 'hold'})
        self.git('add', '--', path)
        self.git('commit', '-qm', preview['git_subject'])
        payload['checkpoint'] = self.git('rev-parse', 'HEAD')
        rejected = self.call(*args, body=payload, valid=False)
        self.assertIn('exact selected transition', rejected['refused'])
        self.fixture_file(path, preview['decision'])
        self.git('add', '--', path)
        self.git('commit', '-qm', preview['git_subject'])
        tip = self.git('rev-parse', 'HEAD')
        # An identical tree on a different history is not the same checkpoint.
        orphan = self.git('commit-tree', self.git('rev-parse', 'HEAD^{tree}'), '-m', preview['git_subject'])
        self.git('reset', '--soft', orphan)
        self.assertTrue(self.call('status', self.state)['checkpoint_flags'])
        rejected = self.call(*args, body={**payload, 'checkpoint': orphan}, valid=False)
        self.assertIn('first-parent history', rejected['refused'])
        self.git('reset', '--soft', tip)
        self.call(*args, body={**payload, 'checkpoint': tip})

    def test_optional_timeout_and_mandatory_gate_hold_allow_independent_work_only(self):
        self.lifecycle('start-scoping')
        self.lifecycle('start-planning', {'charter_ref': 'charter.md'})
        route = {'kind': 'pool', 'fixed_role': None, 'assignee': 'approved-reader', 'handoff': 'eligible',
                 'required': False, 'reason': 'independent optional archive retrieval'}
        assessment = self.apply('assess-task', self.assessment('optional', routing=route))['op_id']
        brief = self.brief_payload('optional') | {'assessment_id': assessment, 'assignee': 'approved-reader',
                                                  'routing_reason': route['reason']}
        self.apply('issue', brief)
        self.apply('mark-ready', {'id': brief['id'], 'basis': 'fixture independent retrieval'})
        self.apply('reserve', {'id': 'optional-attempt', 'revision_id': brief['id'], 'profile_ref': 'fixture'})
        self.apply('attach-run', {'id': 'optional-attempt', 'run_id': 'optional-timeout', 'evidence': 'fixture launch'})
        self.apply('observe-termination', {'id': 'optional-attempt', 'evidence': 'fixture exit observed'})
        self.apply('record-no-result', {'id': 'optional-attempt', 'evidence': 'fixture no usable output'})
        rejected = self.apply('decision', {'id': 'optional-rejected', 'attempt_id': 'optional-attempt',
                                           'verdict': 'rejected', 'rationale': 'optional source unavailable'})
        self.assertEqual(rejected['record_id'], 'optional-rejected')
        self.finish('independent-before-review')
        target = {'gate': 'PLAN_GATE', 'phase': 'protocol'}
        required_review = self.apply('assess-task', self.assessing('required-review',
                                      triggers=['stage-review-gate'], gate=target))['op_id']
        self.review('protocol', 'advisor-unavailable', route=None, assessment_id=required_review,
                    failure='fixture Advisor process unavailable')
        self.call('check-task', self.state, required_review, valid=False)
        status = self.call('status', self.state)
        self.assertEqual(status['status'], 'active')
        self.assertEqual(status['gate_holds'][0]['id'], 'advisor-unavailable')
        self.assertEqual(self.call('next', self.state)['candidates'][0]['action'], 'checkpoint-gate-hold')
        self.lifecycle('checkpoint-gate-hold', {'id': 'advisor-unavailable'})
        self.assertEqual(self.call('next', self.state)['candidates'][0]['action'], 'resolve-gate-hold')
        self.finish('independent-during-gate-hold')
        self.review('protocol', 'premature-re-review', valid=False)
        triage_sha = self.fixture_file('triage.txt', 'pinned independent triage observation')
        self.resolve_gate_hold('advisor-unavailable', 'bounded Advisor re-request after fresh packet review',
                               {'triage.txt': triage_sha})
        (self.root / 'triage.txt').write_text('drift')
        stale = self.review('protocol', 'stale-triage-retry', valid=False)
        self.assertIn('artifact drift: triage.txt', stale['refused'])
        (self.root / 'triage.txt').write_text('pinned independent triage observation')
        self.review('protocol', 'recovered-advisor-review', assessment_id=required_review)
        self.assertEqual(self.call('status', self.state)['stage'], 'IMPLEMENTING')
        self.assertEqual(self.call('status', self.state)['gate_holds'], [])

    def test_gate_hold_is_immediate_but_resume_requires_checkpoint(self):
        self.lifecycle('start-scoping')
        self.lifecycle('start-planning', {'charter_ref': 'charter.md'})
        self.review('protocol', 'block-before-commit', verdict='block', route=None)
        status = self.call('status', self.state)
        self.assertEqual(status['status'], 'active')
        self.assertEqual(status['pending_gate_hold_checkpoint'], 'block-before-commit')
        self.lifecycle('resolve-hold', {'resolution': 'not yet'}, valid=False)
        self.lifecycle('checkpoint-gate-hold', {'id': 'block-before-commit'})
        self.assertEqual(self.call('status', self.state)['status'], 'active')
        self.resolve_gate_hold('block-before-commit', 'fixture evidence triaged')
        self.assertIsNone(self.call('status', self.state)['pending_gate_hold_checkpoint'])

    def test_invalid_or_stale_verdict_cannot_advance(self):
        self.lifecycle('start-scoping')
        self.lifecycle('start-planning', {'charter_ref': 'charter.md'})
        self.review('protocol', 'protocol-review', route=None)
        self.artifact.write_text('changed after review')
        self.lifecycle('gate-route', {'id': 'protocol-review', 'route': 'continue'}, valid=False)
        self.assertTrue(self.call('status', self.state)['gate_flags'])
        self.lifecycle('begin-inner-attempt', valid=False)
        self.lifecycle('withdraw-stale-review', {'id': 'protocol-review'})
        self.hashes['artifact.txt'] = hashlib.sha256(self.artifact.read_bytes()).hexdigest()
        self.review('protocol', 'corrected-protocol')

    def test_cap_preserves_in_plan_repair_and_block_precedence(self):
        for cycle in range(1, 4):
            self.open_cycle(str(cycle), initial=cycle == 1)
            if cycle < 3:
                self.review('cycle', f'c-{cycle}', route='replan',
                            extra={'proposed_route': 'replan', 'next_plan': f'v{cycle + 1}', 'replan_rationale': 'trial'})
        self.review('cycle', 'revise-at-cap', verdict='revise', route=None)
        self.lifecycle('gate-route', {'id': 'revise-at-cap', 'route': 'replan'}, valid=False)
        self.lifecycle('gate-route', {'id': 'revise-at-cap', 'route': 'remediate-plan'}, valid=False)
        self.lifecycle('gate-route', {'id': 'revise-at-cap', 'route': 'remediate-implementation'})
        self.integrate_attempt('repair within final cycle\n')
        self.review('readiness', 'repair-ready')
        self.review('complete', 'repair-exit')
        self.review('cycle', 'block-at-cap', verdict='block', route=None)
        view = self.call('status', self.state)
        self.assertEqual((view['status'], view['cycles_used']), ('active', 3))
        self.assertEqual(view['gate_holds'][0]['id'], 'block-at-cap')
        self.lifecycle('suspend-held', {'status_report': 'not confirmed'}, valid=False)

    def test_malformed_gate_result_records_no_verdict_and_bounds_retries(self):
        self.lifecycle('start-scoping')
        self.lifecycle('start-planning', {'charter_ref': 'charter.md'})
        for i in range(4):
            body = {'id': f'no-verdict-{i}', 'gate': 'PLAN_GATE', 'phase': 'protocol',
                    'manifest': {'id': 'bad@v1', 'gate': 'PLAN_GATE', 'phase': 'protocol', 'artifacts': self.hashes},
                    'advisor_run_id': f'bad-run-{i}', 'verdict': {'gate': 'CYCLE_GATE'}}
            r = self.lifecycle('gate-review', body, valid=i < 3)
            if i < 3:
                self.assertEqual(r['verdict'], 'none')
                self.assertEqual(self.call('status', self.state)['status'], 'active')
                self.resolve_gate_hold(f'no-verdict-{i}', 'bounded retry fixture')
        self.lifecycle('begin-inner-attempt', valid=False)

    def test_protocol_artifact_inventory_blocks_missing_roles_and_wrong_charter(self):
        self.lifecycle('start-scoping')
        self.lifecycle('start-planning', {'charter_ref': 'charter.md'})
        expected = self.gate_manifest('protocol', 'protocol-missing')
        roles = expected['artifact_roles'].copy()
        del roles['hypotheses']
        failed = self.review('protocol', 'protocol-missing', route=None, extra={'artifact_roles': roles})
        self.assertEqual(failed['verdict'], 'none')
        self.assertIn('hypotheses', self.get('protocol-missing')['failure'])
        self.resolve_gate_hold('protocol-missing', 'fixture: add hypotheses')
        wrong_charter = self.fixture_file('previous-charter.md', 'fixture superseded charter')
        wrong = expected | {'artifact_roles': expected['artifact_roles'] | {'charter': 'previous-charter.md'},
                            'artifacts': expected['artifacts'] | {'previous-charter.md': wrong_charter}}
        state = json.loads(self.state.read_text())
        with self.assertRaisesRegex(ValueError, 'active project charter'):
            check_submission(state, wrong, 'PLAN_GATE', 'protocol', self.root)
        approved = self.review('protocol', 'with-artifacts')
        self.assertEqual(approved['verdict'], 'approve')

    def test_diagnosis_only_does_not_waive_raw_results_or_allow_success(self):
        self.start_implementation()
        self.review('readiness', 'ready-for-eval')
        evidence = self.gate_manifest('complete', 'no-raw-results')
        roles = evidence['artifact_roles'].copy()
        del roles['raw-results']
        bad = self.review('complete', 'no-raw-results', route=None, extra={'artifact_roles': roles})
        self.assertEqual(bad['verdict'], 'none')
        self.assertIn('raw-results', self.get('no-raw-results')['failure'])
        self.resolve_gate_hold('no-raw-results', 'fixture: investigate what is missing')
        bad = self.review('diagnosis', 'budget-still-available', route=None,
                          extra={'diagnosis': {'reason': 'attempt-budget-exhausted', 'gaps': ['no valid results'],
                                               'rationale': 'incorrect exhaustion assertion'}})
        self.assertEqual(bad['verdict'], 'none')
        self.assertIn('unspent', self.get('budget-still-available')['failure'])
        self.resolve_gate_hold('budget-still-available', 'fixture: show actual need for a plan change')
        self.review('diagnosis', 'diagnosis-only', route=None)
        self.lifecycle('gate-route', {'id': 'diagnosis-only', 'route': 'continue'}, valid=False)
        self.lifecycle('gate-route', {'id': 'diagnosis-only', 'route': 'continue-to-diagnose'})
        self.lifecycle('objective', {'id': 'O-1', 'status': 'met', 'evidence_refs': ['artifact.txt']})
        self.review('cycle', 'cannot-report-diagnosis', route=None, extra={'proposed_route': 'report'})
        self.lifecycle('gate-route', {'id': 'cannot-report-diagnosis', 'route': 'report'}, valid=False)
        self.assertEqual(self.call('status', self.state)['stage'], 'ANALYZING')

    def test_cycle_proposal_binds_active_cycle_and_forward_route(self):
        self.open_cycle('1', initial=True)
        m = self.gate_manifest('cycle', 'wrong-cycle')
        rel = m['artifact_roles']['cycle-decision']
        record = json.loads((self.root / rel).read_text())
        m['artifacts'][rel] = self.fixture_file(rel, record | {'cycle': 3})
        check_manifest(m, 'CYCLE_GATE', 'cycle', self.root)  # Shape and hashes alone are insufficient.
        state = json.loads(self.state.read_text())
        with self.assertRaisesRegex(ValueError, 'different cycle or plan'):
            check_submission(state, m, 'CYCLE_GATE', 'cycle', self.root)
        self.lifecycle('objective', {'id': 'O-1', 'status': 'met', 'evidence_refs': ['artifact.txt']})
        result = self.review('cycle', 'wrong-forward-route', route=None, extra={'proposed_route': 'hold'})
        self.assertEqual(result['verdict'], 'none')
        self.assertIn('cover the report route', self.get('wrong-forward-route')['failure'])

    def test_final_report_requires_exact_verification_and_final_manifest(self):
        m = self.gate_manifest('report', 'draft')
        check_manifest(m, 'REPORT_GATE', 'report', self.root)
        path = m['artifact_roles']['verification']
        record = json.loads((self.root / path).read_text())
        record['artifacts'][m['artifact_roles']['report']] = '0' * 64
        m['artifacts'][path] = self.fixture_file(path, record)
        with self.assertRaisesRegex(ValueError, 'exact mandatory report artifact hashes'):
            check_manifest(m, 'REPORT_GATE', 'report', self.root)
        m = self.gate_manifest('report', 'draft')
        path = m['artifact_roles']['final-manifest']
        record = json.loads((self.root / path).read_text())
        del record['artifacts'][m['artifact_roles']['claim-evidence-matrix']]
        m['artifacts'][path] = self.fixture_file(path, record)
        with self.assertRaisesRegex(ValueError, 'final artifact manifest must pin'):
            check_manifest(m, 'REPORT_GATE', 'report', self.root)

    def test_manifest_coverage_and_freshness(self):
        roles = self.gate_manifest('protocol', 'protocol')['artifact_roles']
        self.fixture_file('roles.json', roles)
        args = SimpleNamespace(id='protocol@1', gate='PLAN_GATE', phase='protocol', paths=['artifact.txt'],
                               required_test=['unit'], artifact_roles=self.root / 'roles.json', phase_evidence=None)
        reviewed = manifest(self.root, args)
        cli = subprocess.run([sys.executable, '-B', HERE / 'checks.py', 'manifest', self.root, 'PLAN_GATE',
                              'protocol', 'protocol@1', 'artifact.txt', '--required-test', 'unit',
                              '--artifact-roles', args.artifact_roles], capture_output=True, text=True, timeout=10)
        self.assertEqual(cli.returncode, 0, cli.stdout + cli.stderr)
        self.assertEqual(json.loads(cli.stdout), reviewed)
        self.assertTrue(coverage(self.root, reviewed, reviewed)['covers_same_bytes'])
        self.artifact.write_text('changed intentionally')
        args.id = 'protocol@2'
        self.assertEqual(coverage(self.root, reviewed, manifest(self.root, args))['changed'], ['artifact.txt'])
        self.lifecycle('start-scoping')
        stale = freshness(self.state, {'state_revision': 0, 'as_of': '2026-01-01T00:00:00+00:00',
                                      'stale_after': {'brief': '2026-01-02T00:00:00+00:00'}}, '2026-01-03T00:00:00+00:00')
        self.assertEqual(len(stale['flags']), 2)

    def test_pool_profile_comparison_rejects_drift_and_indirect_delegation(self):
        observed = {'name': 'paper-extractor', 'definition_sha256': 'a' * 64, 'model': 'provider/model',
                    'override_source': 'explicit launch', 'tools': ['read', 'codemode'],
                    'indirect_tools': ['read'], 'model_endpoints': []}
        approved = {'operator': 'director', 'profile': observed}
        self.assertTrue(pool_profile(approved, {**observed, 'tools': ['codemode', 'read']})['matches'])
        with self.assertRaisesRegex(ValueError, 'drift'):
            pool_profile(approved, {**observed, 'model': 'provider/fallback'})
        bad = {**observed, 'indirect_tools': ['subagent']}
        with self.assertRaisesRegex(ValueError, 'prohibited'):
            pool_profile({'operator': 'director', 'profile': bad}, bad)

    def test_reference_analysis_is_reproducible_and_limits_claims(self):
        config = self.root / 'config.json'
        config.write_text(json.dumps({'metric': 'accuracy', 'baseline': 'b', 'candidate': 'c', 'seed': 71,
                                      'samples': 1500, 'limitation': 'constructed observations only', 'inputs': self.hashes}))
        raw = self.root / 'obs.csv'
        raw.write_text('example_id,baseline,candidate\n' + ''.join(f'{i},0,{i % 2}\n' for i in range(12)))
        r = analyze(self.root, config, raw)
        self.assertEqual(r, analyze(self.root, config, raw))
        self.assertEqual(r['paired_mean_delta'], 0.5)
        self.assertIn('not an Advisor verdict', draft(r))


if __name__ == '__main__':
    unittest.main()
