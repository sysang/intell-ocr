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
        return self.apply(action, body or {}, group='lifecycle', valid=valid)

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
        manifest = {**target, 'id': 'real-review@v1', 'artifacts': self.hashes, 'required_tests': ['unit']}
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
        manifest = {**target, 'id': 'uncounted@v1', 'artifacts': self.hashes, 'required_tests': ['unit']}
        attempt = self.lifecycle('reserve-consultation', self.advisor_request(key, 'gate', manifest=manifest))['op_id']
        self.settle_advisor(attempt, 'run-uncounted', tokens=None)
        review = self.review('protocol', 'uncounted', assessment_id=key, attempt_id=attempt, route=None)
        self.assertEqual(review['verdict'], 'none')
        self.assertEqual(self.call('status', self.state)['status'], 'hold')
        self.lifecycle('gate-route', {'id': 'uncounted', 'route': 'continue'}, valid=False)

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

    def readiness_manifest(self, slug):
        protocol = next(key for key, record in reversed(self.call('show', 'gate_reviews', self.state).items())
                        if record['phase'] == 'protocol' and record['route'] == 'continue')
        output = self.root / f'{slug}-tests.log'
        output.write_text(f'fixture test observations for {slug}\n')
        baseline = self.root / 'src/method.py'
        artifacts = self.hashes | {p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in (output, baseline)}
        return {'id': f'{slug}@v1', 'gate': 'PLAN_GATE', 'phase': 'readiness', 'artifacts': artifacts,
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

    def check_okf(self, manifest, *, publication=None, valid=True):
        if publication is None:
            request = self.begin_okf()
            self.prepare_okf(request)
            publication = self.publish_okf(request)
        return self.lifecycle('check-okf-gate', {'manifest': manifest, 'writer_result': publication['writer_result'],
                              'publication_id': publication['op_id'], 'hub_sha256': hub_fingerprint(self.root),
                              'service_artifacts': publication['writer_artifacts']}, valid=valid)

    def review(self, phase, slug, *, verdict='approve', route='continue', extra=None, valid=True, check_okf=True,
               assessment_id=None, attempt_id=None, run_id=None):
        gate = {'protocol':'PLAN_GATE', 'readiness':'PLAN_GATE', 'complete':'INNER_EXIT_GATE', 'diagnosis':'INNER_EXIT_GATE',
                'cycle':'CYCLE_GATE', 'report':'REPORT_GATE'}[phase]
        m = {'gate': gate, 'phase': phase, 'id': f'{slug}@v1', 'artifacts': self.hashes}
        if phase == 'protocol':
            m['required_tests'] = ['unit']
        elif phase == 'readiness':
            m = self.readiness_manifest(slug)
        m.update(extra or {})
        output = {'gate': gate, 'review_target': m['id'], 'verdict': verdict, 'summary': 'synthetic review fixture',
                  'findings': [], 'alternative_explanations': [], 'residual_uncertainties': [],
                  'recommended_next_actions': [], 'additional_evidence_required': []}
        if verdict in ('revise', 'block'):
            output['findings'] = [{'severity': 'major', 'issue': 'fixture gap', 'justification': 'check',
                                   'evidence_refs': ['artifact.txt'], 'required_action': 'triage'}]
        if verdict == 'inconclusive':
            output['additional_evidence_required'] = ['fixture']
        payload = {'id': slug, 'gate': gate, 'phase': phase, 'manifest': m,
                   'advisor_run_id': run_id or f'run-{slug}', 'verdict': output}
        if assessment_id:
            payload['assessment_id'] = assessment_id
        if attempt_id:
            payload['attempt_id'] = attempt_id
        if valid and check_okf and requires_okf(m):
            payload['okf_check'] = self.check_okf(m)['op_id']
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
            self.assertEqual(self.call('status', self.state)['status'], 'hold')
            self.lifecycle('resolve-hold', {'resolution': 'fixture: corrected submission'})
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
        manifest = {'id': 'precheck@v1', 'gate': 'CYCLE_GATE', 'phase': 'cycle', 'artifacts': self.hashes}
        request = self.begin_okf()
        self.prepare_okf(request, writer_bytes=b'{', valid=False)
        self.prepare_okf(request)
        publication = self.publish_okf(request)
        self.check_okf({**manifest, 'okf_reader_required': True}, publication=publication, valid=False)
        result = self.review('cycle', 'missing-check', route=None, check_okf=False)
        self.assertEqual(result['verdict'], 'none')
        self.assertEqual(self.call('status', self.state)['status'], 'hold')
        self.lifecycle('resolve-hold', {'resolution': 'fixture: fresh valid OKF evidence'})
        self.review('cycle', 'ready-check', route=None)
        check = self.get('ready-check')['okf_check']
        other = self.check_okf(manifest, publication=self.get(self.get(check)['publication_id']))['op_id']
        self.assertNotEqual(check, other)
        self.lifecycle('gate-route', {'id': 'ready-check', 'route': 'hold', 'reason': 'fixture', 'okf_check': other},
                       valid=False)
        self.lifecycle('gate-route', {'id': 'ready-check', 'route': 'hold', 'reason': 'fixture'})

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
        self.assertEqual(self.get('cycle-review')['routed_okf_check'], refreshed)

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

        args = self.args('lifecycle', 'start-planning')
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
                args = self.args('lifecycle', 'gate-route')
                out = self.call(*args, body=payload)
                self.rev = out['revision']
                self.assertTrue(self.call(*args, body=payload)['replayed'])
                self.lifecycle('gate-route', payload, valid=False)
            else:
                self.lifecycle('objective', {'id': 'O-1', 'status': 'met', 'evidence_refs': ['artifact.txt']})
                self.review('cycle', 'cycle-final', route='report')
        self.review('report', 'final-report', route='complete')
        view = self.call('status', self.state)
        self.assertEqual((view['outer_cycle'], view['cycles_used'], view['stage']), (3, 3, 'COMPLETED'))

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
        self.assertEqual((view['status'], view['cycles_used']), ('hold', 3))
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
                self.assertEqual(self.call('status', self.state)['status'], 'hold')
                self.lifecycle('resolve-hold', {'resolution': 'bounded retry fixture'})
        self.lifecycle('begin-inner-attempt', valid=False)

    def test_manifest_coverage_and_freshness(self):
        args = SimpleNamespace(id='protocol@1', gate='PLAN_GATE', phase='protocol', paths=['artifact.txt'],
                               required_test=['unit'])
        reviewed = manifest(self.root, args)
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
