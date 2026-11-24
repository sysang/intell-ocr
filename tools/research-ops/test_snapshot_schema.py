"""Managed snapshot coverage: schema, cross-record checks, and CLI refusal."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import durable
import ledger
import snapshot_schema

HERE = Path(__file__).parent.resolve()
TIME = '2026-01-01T00:00:00+00:00'


class SnapshotSchemaTests(unittest.TestCase):
    def setUp(self):
        self.state = durable.new_state('schema-pilot', ['Check state shape'], 3, 2, 'charter.md', 2)

    def test_nested_shape_errors_report_the_actual_field(self):
        cases = (
            ('$.lifecycle', lambda state: state.update(lifecycle=[])),
            ('$.budgets.outer_cycles.used', lambda state: state['budgets']['outer_cycles'].update(used=True)),
            ('$.objectives[0].evidence_refs', lambda state: state['objectives'][0].update(evidence_refs='not a list')),
            ('$.execution.briefs', lambda state: state['execution']['briefs'].update(brief={'id': 'brief', 'recorded_at': TIME})),
            ('$.gate_reviews', lambda state: state['gate_reviews'].update(review={'cycle': 1})),
        )
        for path, corrupt in cases:
            with self.subTest(path=path):
                snapshot = copy.deepcopy(self.state)
                corrupt(snapshot)
                self.assertTrue(any(error.startswith(f'managed schema {path}') for error in durable.validate(snapshot)))

    def test_relational_errors_are_separate_from_schema_shape(self):
        state, _ = durable.apply(self.state, 'lifecycle', 'start-scoping', {}, 'scope', 0, 'fixture', 'scope', TIME, HERE)
        self.assertFalse(snapshot_schema.violations(state))
        state['operations']['scope']['op_id'] = 'forged'
        self.assertFalse(snapshot_schema.violations(state))
        self.assertIn('invalid operation receipts', '; '.join(durable.validate(state)))
        self.state['objectives'][0]['status'] = 'met'
        self.assertIn('no evidence_refs', '; '.join(durable.validate(self.state)))

    def test_broken_snapshot_blocks_reads_and_mutations_without_rewriting_it(self):
        with tempfile.TemporaryDirectory() as folder:
            snapshot = Path(folder) / 'project-state.json'
            self.state['lifecycle']['inner_attempt'] = 'not a number'
            data = json.dumps(self.state)
            snapshot.write_text(data)
            commands = (
                ['validate', snapshot], ['status', snapshot], ['get', snapshot, 'review'],
                ['apply', snapshot, 'lifecycle', 'start-scoping', '--input', '-', '--op-id', 'scope',
                 '--expected-revision', '0', '--actor', 'fixture', '--reason', 'test'],
            )
            for cmd in commands:
                with self.subTest(command=cmd[0]):
                    proc = subprocess.run([sys.executable, '-B', HERE / 'ledger.py', *cmd],
                                          capture_output=True, text=True, input='{}', timeout=10)
                    self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                    self.assertFalse(proc.stderr)
                    self.assertIn('$.lifecycle.inner_attempt', proc.stdout)
                    self.assertEqual(snapshot.read_text(), data)

    def test_missing_format_cannot_bypass_managed_validation(self):
        del self.state['format']
        self.assertTrue(ledger.check_invariants(self.state))

    def test_ambiguous_and_nonfinite_json_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            snapshot = Path(folder) / 'project-state.json'
            for raw in ('{"format": 1, "format": 2}', '{"revision": NaN}', '{"revision": 1e999}'):
                with self.subTest(raw=raw):
                    snapshot.write_text(raw)
                    self.assertIn('state file unreadable', ledger.check_invariants(ledger.load_state(snapshot))[0])

    def test_missing_validator_fails_closed(self):
        snapshot_schema.validator.cache_clear()
        with patch.dict(sys.modules, {'jsonschema': None}):
            self.assertIn('install tools/research-ops/requirements.txt', '; '.join(durable.validate(self.state)))
