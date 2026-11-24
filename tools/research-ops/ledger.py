#!/usr/bin/env python3
"""Research-project live-ledger CLI (blueprint §8.8, toolset §10.7).

Awareness as derivation, not recollection: every read of project-state.json
goes through invariant checks, and status/next/progress/termination views are
computed from the snapshot. Views carry generation metadata; a stale view is
labeled stale, never silently trusted.

Managed writes: init and apply. Exact reads: get (evidence and gate IDs).
Legacy advance is dry-run only. See the runbook for guarded payloads.

Usage:
  ledger.py validate <state.json>
  ledger.py status <state.json>
  ledger.py next <state.json>
  ledger.py progress <state.json>
  ledger.py termination-check <state.json>
  ledger.py show <section> <state.json>
  ledger.py advance <state.json> --event EVENT [event args...]

Exit codes: 0 ok (for termination-check: 0 whichever predicate fires; the
fired predicate is in the output). 1 invariant violation / illegal event.
2 usage error.
"""

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import subprocess

import durable
import evidence
import gates

MAX_REVISE_ROUNDS = 2
EARLY_STOP_DEFAULT = 2
STAGES = ["CREATED", "SCOPING", "PLANNING", "IMPLEMENTING",
          "EVALUATING", "ANALYZING", "REPORTING", "COMPLETED"]
GATE_ORDER = ["PLAN_GATE", "INNER_EXIT_GATE", "CYCLE_GATE", "REPORT_GATE"]


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat()


def load_state(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        return {"__load_error__": str(exc)}


def check_invariants(state):
    """Return a list of violation strings; empty means the snapshot is sound."""
    problems = []
    if not isinstance(state, dict):
        return ["state must be a JSON object"]
    if "__load_error__" in state:
        return ["state file unreadable: " + state["__load_error__"]]
    for top in ("identity", "lifecycle", "budgets", "objectives",
                "progress_verdicts", "gates", "blockers",
                "assignments", "consultations", "decisions"):
        if top not in state:
            problems.append("missing top-level section: %s" % top)
    if problems:
        return problems
    lc = state["lifecycle"]
    if lc.get("stage") not in STAGES:
        problems.append("unknown stage: %r" % (lc.get("stage"),))
    if lc.get("status") not in ("active", "hold", "suspended"):
        problems.append("unknown status: %r" % (lc.get("status"),))
    oc, bc = lc.get("outer_cycle"), state["budgets"]["outer_cycles"]
    if not isinstance(oc, int) or oc < 1:
        problems.append("outer_cycle must be an integer >= 1")
    if not isinstance(bc.get("used"), int) or bc["used"] < 0:
        problems.append("budgets.outer_cycles.used must be an integer >= 0")
    if isinstance(oc, int) and isinstance(bc.get("used"), int) and bc["used"] > oc:
        problems.append("budgets used (%d) exceeds outer_cycle (%d)" % (bc["used"], oc))
    if not (3 <= bc.get("max", 0) <= 5):
        problems.append("budgets.outer_cycles.max must be in [3, 5] (charter range)")
    for name, g in state["gates"].items():
        if g.get("verdict") not in ("approve", "revise", "inconclusive", "block", "none"):
            problems.append("gate %s has unknown verdict %r" % (name, g.get("verdict")))
        if not isinstance(g.get("rounds_used"), int) or g["rounds_used"] < 0:
            problems.append("gate %s has bad rounds_used" % name)
        if g["rounds_used"] > MAX_REVISE_ROUNDS and g.get("verdict") in ("revise", "inconclusive"):
            problems.append("gate %s exceeded max revise rounds without HOLD" % name)
        if g.get("verdict") == "approve" and not g.get("target_manifest"):
            problems.append("gate %s approved with empty target_manifest" % name)
    legacy = state["assignments"]
    if not isinstance(legacy, list):
        problems.append("legacy assignments must be a list")
    else:
        required = {"assignment_id", "base_revision", "workspace_ref", "status"}
        optional = {"run_id", "result", "acceptance"}
        ids = set()
        for index, a in enumerate(legacy):
            if (not isinstance(a, dict) or not required <= a.keys() or a.keys() - required - optional or
                    any(not isinstance(a[key], str) or not a[key].strip() for key in required) or
                    a["status"] not in ("dispatched", "returned", "accepted", "rejected") or
                    a.get("result", "none") not in ("success", "partial", "blocked", "none") or
                    a.get("acceptance", "pending") not in ("accepted", "rejected", "pending") or
                    (a.get("run_id") is not None and not isinstance(a["run_id"], str))):
                problems.append("invalid legacy assignment at index %d" % index)
            elif a["assignment_id"] in ids:
                problems.append("duplicate legacy assignment ID: %s" % a["assignment_id"])
            else:
                ids.add(a["assignment_id"])
    for o in state["objectives"]:
        if o.get("status") not in ("untested", "partial", "met", "failed"):
            problems.append("objective %s has unknown status" % o.get("id"))
        if o.get("status") == "met" and not o.get("evidence_refs"):
            problems.append("objective %s marked met with no evidence_refs" % o.get("id"))
    if lc.get("status") == "suspended" and lc.get("stage") != "COMPLETED":
        # SUSPENDED is terminal-but-not-complete; allowed only with a recorded report trail.
        ok = bool(lc.get('status_report')) if 'format' in state else (
            any(d.get('status') in ('closed', 'superseded') for d in state['decisions']) or
            any(b.get('status') == 'confirmed-unresolvable' for b in state['blockers']))
        if not ok:
            problems.append("SUSPENDED with no closed decision or confirmed-unresolvable blocker on record")
    return problems + (durable.validate(state) if 'format' in state else [])


def generation_meta(state_path):
    return {"generated_at": now_iso(), "source": state_path}


def cmd_status(state, meta):
    lc, bc = state["lifecycle"], state["budgets"]["outer_cycles"]
    open_blockers = [b["id"] for b in state["blockers"] if b["status"] == "open"]
    open_decisions = [d["id"] for d in state["decisions"] if d["status"] == "open"]
    gate_readiness = {}
    for name in GATE_ORDER:
        g = state["gates"].get(name)
        if g is None:
            gate_readiness[name] = "not-recorded"
        elif g["verdict"] == "approve" and g["target_manifest"]:
            gate_readiness[name] = "satisfied"
        elif g["rounds_used"] >= MAX_REVISE_ROUNDS and g["verdict"] in ("revise", "inconclusive"):
            gate_readiness[name] = "rounds-exhausted-HOLD"
        else:
            gate_readiness[name] = "open"
    return {"meta": meta, "stage": lc["stage"], "status": lc["status"],
            "hold_reason": lc.get("hold_reason"),
            "outer_cycle": lc["outer_cycle"], "inner_attempt": lc["inner_attempt"],
            "plan_version": lc["plan_version"],
            "cycles_used": bc["used"], "cycles_max": bc["max"],
            "cycles_remaining": max(0, bc["max"] - bc["used"]),
            "open_blockers": open_blockers, "open_decisions": open_decisions,
            "gate_readiness": gate_readiness}


def cmd_next(state, meta):
    """Eligible CANDIDATE next actions with their basis. The Lead selects."""
    lc = state["lifecycle"]
    cands = []
    if lc["status"] == "suspended":
        return {"meta": meta, "candidates": []}
    if lc["status"] == "hold":
        cands.append({"action": "triage-hold",
                      "basis": "hold_reason=%s" % lc.get("hold_reason")})
        return {"meta": meta, "candidates": cands}
    if any(b["status"] == "open" for b in state["blockers"]):
        cands.append({"action": "triage-blocker",
                      "basis": "open blockers present"})
    if any(d["status"] == "open" and d["tag"] == "DECISION-REQUIRED"
           for d in state["decisions"]):
        cands.append({"action": "resolve-director-decision",
                      "basis": "open DECISION-REQUIRED entries"})
    plan = state["gates"].get("PLAN_GATE", {})
    if lc["stage"] == "PLANNING" and plan.get("verdict") != "approve":
        cands.append({"action": "request-PLAN_GATE-review",
                      "basis": "stage=PLANNING, PLAN_GATE verdict=%s, rounds %d/%d"
                               % (plan.get("verdict"), plan.get("rounds_used", 0),
                                  MAX_REVISE_ROUNDS)})
    if lc["stage"] in ("IMPLEMENTING", "EVALUATING"):
        cands.append({"action": "continue-inner-loop-or-exit",
                      "basis": "inner_attempt=%d under %s" % (lc["inner_attempt"],
                                                             lc["plan_version"])})
    cyc = state["gates"].get("CYCLE_GATE", {})
    if lc["stage"] == "ANALYZING" and cyc.get("verdict") != "approve":
        cands.append({"action": "request-CYCLE_GATE-review",
                      "basis": "stage=ANALYZING, CYCLE_GATE verdict=%s" % cyc.get("verdict")})
    if cyc.get("verdict") == "approve" and all(o["status"] == "met" for o in state["objectives"]):
        cands.append({"action": "route-report",
                      "basis": "CYCLE_GATE approve with all objectives met"})
    return {"meta": meta, "candidates": cands}


def cmd_progress(state, meta):
    counts = {"untested": 0, "partial": 0, "met": 0, "failed": 0}
    for o in state["objectives"]:
        counts[o["status"]] = counts.get(o["status"], 0) + 1
    trend = [{"cycle": p["cycle"], "verdict": p["verdict"]}
             for p in sorted(state["progress_verdicts"], key=lambda p: p["cycle"])]
    return {"meta": meta, "objective_counts": counts,
            "objectives_total": len(state["objectives"]),
            "cycle_trend": trend,
            "outer_cycle": state["lifecycle"]["outer_cycle"]}


def termination_predicate(state):
    """Achievement first, then blocker, then stagnation. Returns (name, route, detail)."""
    lc = state["lifecycle"]
    if lc["status"] == "suspended":
        return ("already-suspended", "none", "terminal; no further routes")
    if state["objectives"] and all(o["status"] == "met" for o in state["objectives"]):
        return ("objective-achieved", "report",
                "all %d objectives met; checked before cap" % len(state["objectives"]))
    confirmed = [b["id"] for b in state["blockers"]
                 if b["status"] == "confirmed-unresolvable"]
    if confirmed:
        return ("blocker-confirmed", "suspended+status-report",
                "confirmed-unresolvable: %s" % ",".join(confirmed))
    bc = state["budgets"]["outer_cycles"]
    if bc["used"] >= bc["max"]:
        return ("cycle-cap-reached", "suspended+status-report",
                "used %d of max %d" % (bc["used"], bc["max"]))
    trend = [p["verdict"] for p in sorted(state["progress_verdicts"],
                                          key=lambda p: p["cycle"])]
    if len(trend) >= EARLY_STOP_DEFAULT and all(
            v in ("stalled", "regressed") for v in trend[-EARLY_STOP_DEFAULT:]):
        return ("early-stagnation", "suspended+status-report",
                "last %d cycles: %s" % (EARLY_STOP_DEFAULT, ",".join(trend[-EARLY_STOP_DEFAULT:])))
    return ("no-predicate", "continue",
            "cycles remaining: %d" % (bc["max"] - bc["used"]))


def cmd_termination_check(state, meta):
    name, route, detail = termination_predicate(state)
    return {"meta": meta, "predicate": name, "route": route, "detail": detail}


ADVANCE_EVENTS = ("begin-inner-attempt", "authorize-replan", "consume-revise-round",
                  "record-gate-verdict", "record-progress-verdict", "update-objective",
                  "open-hold", "convert-suspended")


def cmd_advance(state, args):
    """Apply one charged event; returns (new_state, receipt) or (None, error)."""
    event = args.event
    if event not in ADVANCE_EVENTS:
        return None, "unknown event %r; legal: %s" % (event, ",".join(ADVANCE_EVENTS))
    lc, bc = state["lifecycle"], state["budgets"]["outer_cycles"]
    if lc["status"] == "suspended":
        return None, "refused: ledger is SUSPENDED (terminal)"
    new = copy.deepcopy(state)
    nlc, nbc = new["lifecycle"], new["budgets"]["outer_cycles"]
    receipt = {"event": event, "at": now_iso()}
    if event == "begin-inner-attempt":
        nlc["inner_attempt"] += 1
        receipt["charged"] = "inner_attempt=%d" % nlc["inner_attempt"]
    elif event == "authorize-replan":
        if nbc["used"] >= nbc["max"]:
            return None, "refused: cycle cap reached (used %d of %d)" % (nbc["used"], nbc["max"])
        nbc["used"] += 1
        nlc["outer_cycle"] += 1
        nlc["inner_attempt"] = 0
        if args.plan_version:
            nlc["plan_version"] = args.plan_version
        receipt["charged"] = "outer_cycle=%d (used %d of %d)" % (
            nlc["outer_cycle"], nbc["used"], nbc["max"])
    elif event == "consume-revise-round":
        if not args.gate or args.gate not in new["gates"]:
            return None, "consume-revise-round requires --gate with a recorded gate"
        g = new["gates"][args.gate]
        if g["rounds_used"] >= MAX_REVISE_ROUNDS:
            return None, "refused: %s rounds exhausted; HOLD instead" % args.gate
        g["rounds_used"] += 1
        receipt["charged"] = "%s rounds_used=%d" % (args.gate, g["rounds_used"])
    elif event == "record-gate-verdict":
        if not args.gate or args.gate not in new["gates"] or not args.verdict:
            return None, "record-gate-verdict requires --gate and --verdict"
        if args.verdict not in ("approve", "revise", "inconclusive", "block"):
            return None, "bad verdict %r" % args.verdict
        g = new["gates"][args.gate]
        g["verdict"] = args.verdict
        if args.manifest:
            g["target_manifest"] = args.manifest
        g["timestamp"] = now_iso()
        receipt["recorded"] = "%s=%s on %s" % (args.gate, args.verdict, g["target_manifest"])
    elif event == "record-progress-verdict":
        if not args.progress or args.progress not in ("advanced", "marginal", "stalled", "regressed"):
            return None, "record-progress-verdict requires --progress"
        new["progress_verdicts"].append({"cycle": nlc["outer_cycle"],
                                         "verdict": args.progress, "evidence_refs": []})
        receipt["recorded"] = "cycle %d: %s" % (nlc["outer_cycle"], args.progress)
    elif event == "update-objective":
        if not args.objective or not args.obj_status:
            return None, "update-objective requires --objective and --obj-status"
        if args.obj_status not in ("untested", "partial", "met", "failed"):
            return None, "bad objective status %r" % args.obj_status
        match = [o for o in new["objectives"] if o["id"] == args.objective]
        if not match:
            return None, "unknown objective %r" % args.objective
        match[0]["status"] = args.obj_status
        if args.evidence:
            match[0]["evidence_refs"] = args.evidence.split(",")
        if match[0]["status"] == "met" and not match[0]["evidence_refs"]:
            return None, "refused: met requires evidence_refs"
        receipt["recorded"] = "%s=%s" % (args.objective, args.obj_status)
    elif event == "open-hold":
        nlc["status"] = "hold"
        nlc["hold_reason"] = args.reason or "unspecified"
        receipt["recorded"] = "hold: %s" % nlc["hold_reason"]
    elif event == "convert-suspended":
        name, route, _ = termination_predicate(new)
        if name == "no-predicate":
            return None, "refused: no termination predicate fires; SUSPENDED needs cap, stagnation, or confirmed blocker"
        nlc["status"] = "suspended"
        receipt["recorded"] = "suspended via %s" % name
    problems = check_invariants(new)
    if problems:
        return None, "advance produced invalid state: %s" % "; ".join(problems)
    return new, receipt


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ledger.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("validate", "status", "next", "progress", "termination-check"):
        p = sub.add_parser(name)
        p.add_argument("state")
    p = sub.add_parser("show")
    p.add_argument("section")
    p.add_argument("state")
    p = sub.add_parser("advance")
    p.add_argument("state")
    p.add_argument("--event", required=True)
    p.add_argument("--in-place", action="store_true")
    p.add_argument("--gate")
    p.add_argument("--verdict")
    p.add_argument("--manifest")
    p.add_argument("--plan-version")
    p.add_argument("--progress")
    p.add_argument("--objective")
    p.add_argument("--obj-status")
    p.add_argument("--evidence")
    p.add_argument("--reason")
    init = sub.add_parser('init')
    init.add_argument('state')
    init.add_argument('--project', required=True)
    init.add_argument('--objective', action='append', required=True)
    init.add_argument('--outer-limit', type=int, default=4)
    init.add_argument('--inner-limit', type=int, default=3)
    init.add_argument('--stagnation-cycles', type=int, default=2)
    init.add_argument('--charter', default='charter.md')
    apply = sub.add_parser('apply')
    apply.add_argument('state')
    apply.add_argument('group', choices=('evidence', 'lifecycle'))
    apply.add_argument('action')
    apply.add_argument('--input', required=True, help='JSON file or - for stdin')
    apply.add_argument('--op-id', required=True)
    apply.add_argument('--expected-revision', required=True, type=int)
    apply.add_argument('--actor', required=True)
    apply.add_argument('--reason', required=True)
    get = sub.add_parser('get')
    get.add_argument('state')
    get.add_argument('id')
    close = sub.add_parser('check-close')
    close.add_argument('state')
    close.add_argument('task')
    close.add_argument('record')
    close.add_argument('disposition', choices=('accepted', 'dropped'))
    args = ap.parse_args(argv)
    path = Path(args.state).resolve()
    try:
        if args.cmd in ('init', 'apply'):
            with durable.lock(path):
                if args.cmd == 'init':
                    evidence.require(not path.exists(), 'state already exists')
                    new = durable.new_state(args.project, args.objective, args.outer_limit, args.inner_limit,
                                            args.charter, args.stagnation_cycles)
                    receipt = {'revision': 0, 'project': args.project}
                else:
                    state = load_state(path)
                    problems = check_invariants(state)
                    evidence.require(not problems, '; '.join(problems))
                    if args.input == '-':
                        payload = json.load(sys.stdin)
                    else:
                        with open(args.input, encoding='utf-8') as f:
                            payload = json.load(f)
                    new, receipt = durable.apply(state, args.group, args.action, payload, args.op_id,
                                                 args.expected_revision, args.actor, args.reason, now_iso(), path.parent)
                    if new is not None:
                        problems = check_invariants(new)
                        evidence.require(not problems, '; '.join(problems))
                if new is not None:
                    durable.save(path, new)
            print(json.dumps(receipt, indent=2))
            return 0
        state = load_state(path)
        problems = check_invariants(state)
        if not problems and args.cmd in ('get', 'check-close'):
            evidence.require(state.get('format') == 1, 'operation requires managed state')
            if args.cmd == 'get':
                result = ({'kind': 'gate_review', 'record': state['gate_reviews'][args.id]}
                          if args.id in state['gate_reviews'] else evidence.get(state, args.id))
            else:
                evidence.close_check(state, args.task, args.record, args.disposition, path.parent)
                result = {'allowed': True, 'revision': state['revision'], 'project': state['identity']['project_id']}
            print(json.dumps(result, indent=2))
            return 0
    except (ValueError, OSError, TypeError, KeyError, AttributeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({'refused': str(exc)}))
        return 1
    if args.cmd == "validate":
        print(json.dumps({"valid": not problems, "violations": problems}, indent=2))
        return 1 if problems else 0
    if problems:
        print(json.dumps({"error": "invalid ledger; fix before any read",
                          "violations": problems}, indent=2))
        return 1
    meta = generation_meta(args.state)
    if state.get('format') == 1:
        meta['revision'] = state['revision']
    if args.cmd == "status":
        status = cmd_status(state, meta)
        if state.get('format') == 1:
            status.pop('gate_readiness')
            status['gate_reviews'] = [{k: row[k] for k in ('gate', 'phase', 'verdict', 'route')} | {'id': key}
                                      for key, row in state['gate_reviews'].items() if row['cycle'] == status['outer_cycle']]
            status['gate_flags'] = gates.flags(state, path.parent)
            status['execution'] = evidence.view(state['execution'])
        print(json.dumps(status, indent=2))
    elif args.cmd == "next":
        if state.get('format') == 1:
            print(json.dumps({'meta': meta, 'stage': state['lifecycle']['stage'],
                              'status': state['lifecycle']['status'], 'execution': evidence.view(state['execution']),
                              'gate_flags': gates.flags(state, path.parent),
                              'candidates': gates.candidates(state, path.parent)}, indent=2))
        else:
            print(json.dumps(cmd_next(state, meta), indent=2))
    elif args.cmd == "progress":
        print(json.dumps(cmd_progress(state, meta), indent=2))
    elif args.cmd == "termination-check":
        print(json.dumps({'meta': meta, 'predicates': gates.predicates(state)} if state.get('format') == 1
                         else cmd_termination_check(state, meta), indent=2))
    elif args.cmd == "show":
        if args.section not in state:
            print(json.dumps({"error": "unknown section %r" % args.section}))
            return 2
        print(json.dumps(state[args.section], indent=2))
    elif args.cmd == "advance":
        if state.get('format') == 1 or args.in_place:
            print(json.dumps({'refused': 'advance is a legacy dry-run; use guarded apply for managed writes'}))
            return 1
        new, receipt = cmd_advance(state, args)
        if new is None:
            print(json.dumps({"refused": receipt}, indent=2))
            return 1
        print(json.dumps({"receipt": receipt, "state": new}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
