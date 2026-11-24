# Research Lead Pi-tools conversion — todos

Consolidated goal: convert all `tools/research-ops` logic into Pi tools, expose them to Research Lead (and only other relevant agents where justified), encode `README.md` + `consultation-brief.md` into Research Lead via progressive disclosure.

Authority: `blueprint-v1.md` v1.4 semantics unchanged. Python `tools/research-ops` + 85 tests remain the conformance baseline until TS parity is proven. No live delegation, no new spending, no unrelated-plan edits.

## Phase 0 — Design freeze (before any port)
- [ ] Inventory every CLI entrypoint: `ledger.py` (status/next/show/apply/get/check-task/check-close/checkpoint-plan), `checks.py` (manifest/readiness-diff/verdict-still-covers/pool-profile/hub-snapshot/precheck), `research.py` (init/preflight/lead), plus library modules (durable/gates/evidence/task_readiness/consultations/knowledge/hub_publication/gate_artifacts/gate_checkpoints/director/readiness/inner_attempts/snapshot_schema/analyze).
- [ ] Define Pi-tool surface: one tool per operation vs one generic `apply` tool. Decide JSON-schema strictness per action (exact payload shapes from README tables).
- [ ] Define gating: reuse `beads-tools` pattern (`RESEARCH_LEAD_CONFIG` + `RESEARCH_LEAD_PID` + host `MARKER` + `cwd==repo`, `model-only`, `sequential`). Decide which tools (if any) other agents get — default is Lead-only.
- [ ] Define progressive disclosure: agent.md keeps lifecycle map + must-do rules; skill/reference files carry payload tables, checkpoint runbook, OKF publication, consultation accounting, Director runbook; tool `description`/`promptSnippet`/`promptGuidelines` carry call-time rules. No verbatim 218-line paste.
- [ ] Define parity bar: all 85 research-ops + 14 OKF validator behaviors must pass against TS implementation (ported conformance suite), plus `tsc --noEmit` and existing Beads adapter tests.

## Phase 1 — Extension scaffold (no logic port yet)
- [ ] Create `.pi/extensions/research-ledger-tools/` with `index.ts` + `package.json` if needed; verify auto-discovery.
- [ ] Implement 2 read-only thin tools first (`ledger_status`, `ledger_next`) as subprocess wrappers to validate gating, schema plumbing, and test harness.
- [ ] Add `route-governor`-style tests for gating (wrong PID, child env, wrong cwd, missing marker → refused).

## Phase 2 — Logic port (largest risk)
- [ ] Port `snapshot_schema` + `project-state.schema.json` validation (duplicate-JSON-keys, non-finite, receipt bindings) — must leave files unchanged on failure.
- [ ] Port `durable` (revision/op-id idempotency, replay, holds) + `evidence` tables.
- [ ] Port `task_readiness` + `evidence` dispatch actions (issue/mark-ready/reserve/attach/terminate/result/decision/availability/drop).
- [ ] Port `gates` + `readiness` + `gate_artifacts` + `gate_checkpoints` (review/route/reuse/withdraw/resolve-hold, Git first-parent + byte checks).
- [ ] Port `inner_attempts`, `consultations` (mandatory/exploratory budgets, settle/reuse/advice-check), `knowledge` + `hub_publication` (staged publish, resume/abort), `director` (message/delivery/reply/file/stop/reconcile/resume/suspend).
- [ ] Port `checks.py` builders/validators and `research.py` init/preflight (lead launcher stays operator-side).
- [ ] Each module lands with ported unit tests; no module is declared done while Python and TS disagree on any fixture.

## Phase 3 — Prompt encoding with progressive disclosure
- [ ] Rewrite `.pi/agents/research-lead/agent.md`: keep map + non-negotiables; move payload tables to `defaultReads`/skill references (pattern: `imp-worker` frontmatter `defaultReads`).
- [ ] Encode `consultation-brief.md` as a skill checklist referenced by consultation tools, not pasted in full.
- [ ] Tool descriptions carry call-time contracts so the brain sees them only when the tool is relevant.
- [ ] Measure system-prompt size before/after; budget deltas explicitly (full README paste is rejected as the default).

## Phase 4 — Conformance + rollout
- [ ] Port `test_ledger`/`test_managed`/`test_pi_bootstrap`/`test_snapshot_schema` to `node --test`; keep Python suite green until cutover.
- [ ] Dual-run: same fixtures through Python and TS, byte-identical receipts or documented migration.
- [ ] Migration plan for existing `project-state.json` files (read-only legacy + explicit reconcile, no silent rewrite).
- [ ] Docs: update `tools/research-ops/README.md` (or its successor) to point at tools, not `python -B` commands.
- [ ] Commit per phase; never mix with stewardship/ui-verifier changes.

## Concerns (why this is risky)
1. **Correctness:** ~3k lines of ledger semantics + 772-line schema. A subtle divergence (idempotency, HOLD vs gate-hold, checkpoint ancestry) silently corrupts research governance.
2. **Duplication:** two implementations of the same state machine must be kept in lockstep or the old one deleted — mid-migration drift is the failure mode.
3. **Context cost:** exposing ~30 tools + full runbook in-brain on every turn is expensive; progressive disclosure must be real (skills/references/tool-time snippets), not a second paste.
4. **Security:** extensions run with full OS perms. Lead-only gating must be tested like `beads-tools`, not assumed.
5. **Scope creep:** "other relevant agents" must stay default-deny. Worker/Advisor/OKF must never write the ledger directly.
