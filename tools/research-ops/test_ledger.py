#!/usr/bin/env python3
"""Self-tests for ledger.py against fixture ledgers (stdlib unittest only)."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ledger.py")


def base_state(**over):
    s = {
        "identity": {"project_id": "fixture-1", "protocol_version": "1.0",
                     "charter_ref": "charter/v1"},
        "lifecycle": {"stage": "ANALYZING", "status": "active",
                      "outer_cycle": 2, "inner_attempt": 3, "plan_version": "v2",
                      "hold_reason": None},
        "budgets": {"outer_cycles": {"max": 4, "used": 2}},
        "objectives": [
            {"id": "O-1", "text": "beat baseline", "status": "partial",
             "evidence_refs": ["exp/run-3"]},
            {"id": "O-2", "text": "ablate component", "status": "untested",
             "evidence_refs": []}],
        "progress_verdicts": [
            {"cycle": 1, "verdict": "marginal", "evidence_refs": []}],
        "gates": {
            "PLAN_GATE": {"verdict": "approve", "target_manifest": "plan-v2@a1",
                          "rounds_used": 0, "timestamp": "2026-11-22T00:00:00+00:00"},
            "INNER_EXIT_GATE": {"verdict": "approve", "target_manifest": "pkg-7@b2",
                                "rounds_used": 1, "timestamp": "2026-11-22T00:00:00+00:00"},
            "CYCLE_GATE": {"verdict": "none", "target_manifest": "",
                           "rounds_used": 0},
            "REPORT_GATE": {"verdict": "none", "target_manifest": "",
                            "rounds_used": 0}},
        "blockers": [],
        "assignments": [],
        "consultations": [],
        "decisions": [],
    }
    s.update(over)
    return s


class LedgerCase(unittest.TestCase):
    def run_ledger(self, state, *cmd):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(state, fh)
            path = fh.name
        try:
            args = [sys.executable, LEDGER]
            args += [c if c != "STATE" else path for c in cmd]
            r = subprocess.run(args, capture_output=True, text=True, timeout=30)
            return r.returncode, (json.loads(r.stdout) if r.stdout.strip() else None)
        finally:
            os.unlink(path)

    def test_healthy_validates_clean(self):
        code, out = self.run_ledger(base_state(), "validate", "STATE")
        self.assertEqual(code, 0)
        self.assertTrue(out["valid"])

    def test_invalid_legacy_assignment_fails_closed(self):
        state = base_state(assignments=[{"assignment_id": "WORK-014", "status": "invalid"}])
        code, out = self.run_ledger(state, "validate", "STATE")
        self.assertEqual(code, 1)
        self.assertIn("invalid legacy assignment at index 0", out["violations"])
        self.assertEqual(self.run_ledger(state, "status", "STATE")[0], 1)

    def test_status_view(self):
        code, out = self.run_ledger(base_state(), "status", "STATE")
        self.assertEqual(code, 0)
        self.assertEqual(out["stage"], "ANALYZING")
        self.assertEqual(out["cycles_remaining"], 2)
        self.assertEqual(out["gate_readiness"]["CYCLE_GATE"], "open")
        self.assertIn("generated_at", out["meta"])

    def test_next_candidates(self):
        code, out = self.run_ledger(base_state(), "next", "STATE")
        acts = [c["action"] for c in out["candidates"]]
        self.assertIn("request-CYCLE_GATE-review", acts)

    def test_progress_rollup(self):
        code, out = self.run_ledger(base_state(), "progress", "STATE")
        self.assertEqual(out["objective_counts"], {"untested": 1, "partial": 1, "met": 0, "failed": 0})

    def test_termination_continues(self):
        code, out = self.run_ledger(base_state(), "termination-check", "STATE")
        self.assertEqual(out["predicate"], "no-predicate")

    def test_achievement_beats_cap(self):
        s = base_state()
        s["objectives"] = [
            {"id": "O-1", "text": "a", "status": "met", "evidence_refs": ["e"]},
            {"id": "O-2", "text": "b", "status": "met", "evidence_refs": ["e"]}]
        s["budgets"]["outer_cycles"]["used"] = 4
        s["lifecycle"]["outer_cycle"] = 4
        code, out = self.run_ledger(s, "termination-check", "STATE")
        self.assertEqual(out["predicate"], "objective-achieved")
        self.assertEqual(out["route"], "report")

    def test_stagnation_fires(self):
        s = base_state()
        s["progress_verdicts"] = [
            {"cycle": 1, "verdict": "stalled", "evidence_refs": []},
            {"cycle": 2, "verdict": "regressed", "evidence_refs": []}]
        _, out = self.run_ledger(s, "termination-check", "STATE")
        self.assertEqual(out["predicate"], "early-stagnation")

    def test_no_early_stop_on_single_stall(self):
        s = base_state()
        s["progress_verdicts"] = [{"cycle": 1, "verdict": "stalled", "evidence_refs": []}]
        _, out = self.run_ledger(s, "termination-check", "STATE")
        self.assertEqual(out["predicate"], "no-predicate")

    def test_confirmed_blocker_suspends(self):
        s = base_state()
        s["blockers"] = [{"id": "B-1", "description": "x",
                          "status": "confirmed-unresolvable",
                          "since": "2026-11-22T00:00:00+00:00"}]
        _, out = self.run_ledger(s, "termination-check", "STATE")
        self.assertEqual(out["predicate"], "blocker-confirmed")

    def test_advance_charging(self):
        code, out = self.run_ledger(base_state(), "advance", "STATE",
                                    "--event", "begin-inner-attempt")
        self.assertEqual(code, 0)
        self.assertEqual(out["state"]["lifecycle"]["inner_attempt"], 4)
        _, out = self.run_ledger(base_state(), "advance", "STATE",
                                 "--event", "authorize-replan",
                                 "--plan-version", "v3")
        st = out["state"]
        self.assertEqual((st["lifecycle"]["outer_cycle"], st["lifecycle"]["inner_attempt"],
                          st["budgets"]["outer_cycles"]["used"]), (3, 0, 3))
        self.assertEqual(st["lifecycle"]["plan_version"], "v3")

    def test_replan_refused_at_cap(self):
        s = base_state()
        s["budgets"]["outer_cycles"]["used"] = 4
        s["lifecycle"]["outer_cycle"] = 4
        code, out = self.run_ledger(s, "advance", "STATE", "--event", "authorize-replan")
        self.assertEqual(code, 1)
        self.assertIn("refused", out)

    def test_revise_rounds_capped(self):
        s = base_state()
        for _ in range(2):
            code, _ = self.run_ledger(s, "advance", "STATE",
                                      "--event", "consume-revise-round", "--gate", "CYCLE_GATE")
            self.assertEqual(code, 0)
            # feed the advanced state back: emulate by bumping rounds in fixture
            s["gates"]["CYCLE_GATE"]["rounds_used"] += 1
        code, out = self.run_ledger(s, "advance", "STATE",
                                    "--event", "consume-revise-round", "--gate", "CYCLE_GATE")
        self.assertEqual(code, 1)
        self.assertIn("HOLD", out["refused"])

    def test_met_requires_evidence(self):
        code, out = self.run_ledger(base_state(), "advance", "STATE",
                                    "--event", "update-objective",
                                    "--objective", "O-2", "--obj-status", "met")
        self.assertEqual(code, 1)
        code, out = self.run_ledger(base_state(), "advance", "STATE",
                                    "--event", "update-objective",
                                    "--objective", "O-2", "--obj-status", "met",
                                    "--evidence", "exp/run-9")
        self.assertEqual(code, 0)

    def test_suspend_needs_predicate(self):
        code, out = self.run_ledger(base_state(), "advance", "STATE",
                                    "--event", "convert-suspended")
        self.assertEqual(code, 1)
        s = base_state()
        s["budgets"]["outer_cycles"]["used"] = 4
        s["lifecycle"]["outer_cycle"] = 4
        s["decisions"] = [{"id": "D-9", "tag": "FYI", "status": "closed"}]
        code, out = self.run_ledger(s, "advance", "STATE", "--event", "convert-suspended")
        self.assertEqual(code, 0)
        self.assertEqual(out["state"]["lifecycle"]["status"], "suspended")

    def test_invariants(self):
        s = base_state()
        del s["gates"]
        code, out = self.run_ledger(s, "validate", "STATE")
        self.assertEqual(code, 1)
        self.assertTrue(any("gates" in v for v in out["violations"]))
        s = base_state()
        s["objectives"][0]["status"] = "met"
        s["objectives"][0]["evidence_refs"] = []
        _, out = self.run_ledger(s, "validate", "STATE")
        self.assertTrue(any("no evidence" in v for v in out["violations"]))
        s = base_state()
        s["gates"]["CYCLE_GATE"]["verdict"] = "revise"
        s["gates"]["CYCLE_GATE"]["rounds_used"] = 3
        _, out = self.run_ledger(s, "validate", "STATE")
        self.assertTrue(any("rounds" in v for v in out["violations"]))
        s = base_state()
        s["lifecycle"]["status"] = "suspended"
        _, out = self.run_ledger(s, "validate", "STATE")
        self.assertTrue(any("SUSPENDED" in v for v in out["violations"]))
        s = base_state()
        s["budgets"]["outer_cycles"]["max"] = 7
        _, out = self.run_ledger(s, "validate", "STATE")
        self.assertTrue(any("[3, 5]" in v for v in out["violations"]))

    def test_reads_blocked_on_invalid(self):
        s = base_state()
        del s["decisions"]
        code, out = self.run_ledger(s, "status", "STATE")
        self.assertEqual(code, 1)
        self.assertIn("violations", out)


if __name__ == "__main__":
    unittest.main(verbosity=1)
