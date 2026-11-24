"""Offline acceptance/failure-injection tests. Simulated Pi observations, real state and Git."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

from analyze import analyze, draft
from checks import coverage, freshness, manifest, pool_profile

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

    def brief(self, slug='A', *, mode='read', previous_revision=None, base=None):
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
        self.apply('issue', evidence)
        self.apply('mark-ready', {'id': id_, 'basis': 'pinned fixture inputs'})
        return id_

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

    def review(self, phase, slug, *, verdict='approve', route='continue', extra=None):
        gate = {'protocol':'PLAN_GATE', 'readiness':'PLAN_GATE', 'complete':'INNER_EXIT_GATE', 'diagnosis':'INNER_EXIT_GATE',
                'cycle':'CYCLE_GATE', 'report':'REPORT_GATE'}[phase]
        m = {'gate': gate, 'phase': phase, 'id': f'{slug}@v1', 'artifacts': self.hashes, **(extra or {})}
        output = {'gate': gate, 'review_target': m['id'], 'verdict': verdict, 'summary': 'synthetic review fixture',
                  'findings': [], 'alternative_explanations': [], 'residual_uncertainties': [],
                  'recommended_next_actions': [], 'additional_evidence_required': []}
        if verdict in ('revise', 'block'):
            output['findings'] = [{'severity': 'major', 'issue': 'fixture gap', 'justification': 'check',
                                   'evidence_refs': ['artifact.txt'], 'required_action': 'triage'}]
        if verdict == 'inconclusive':
            output['additional_evidence_required'] = ['fixture']
        out = self.lifecycle('gate-review', {'id': slug, 'gate': gate, 'phase': phase, 'manifest': m,
                                             'advisor_run_id': f'run-{slug}', 'verdict': output})
        if route:
            self.lifecycle('gate-route', {'id': slug, 'route': route})
        return out

    def open_cycle(self, suffix, initial=False):
        if initial:
            self.lifecycle('start-scoping')
            self.lifecycle('start-planning', {'charter_ref': 'charter.md'})
        self.review('protocol', f'protocol-{suffix}')
        self.lifecycle('gate-route', {'id': f'protocol-{suffix}', 'route': 'continue'}, valid=False)
        self.lifecycle('begin-inner-attempt')
        self.review('readiness', f'readiness-{suffix}')
        self.review('complete', f'exit-{suffix}')

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
        self.lifecycle('begin-inner-attempt')
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
        args = SimpleNamespace(id='protocol@1', gate='PLAN_GATE', phase='protocol', paths=['artifact.txt'])
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
