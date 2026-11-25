# Research Lead Pi-tools conversion — todos

Consolidated goal (narrowed): migrate only parts of `tools/research-ops` critical to Research Lead skill and knowledge into Pi tools, and encode `README.md` + `consultation-brief.md` via progressive disclosure. Non-critical helpers stay in Python.

Authority: `blueprint-v1.md` v1.4 semantics unchanged. Python `tools/research-ops` + 85 tests remain the conformance baseline until TS parity is proven. No live delegation, no new spending, no unrelated-plan edits.

## Agreed decisions (locked)
- Full cutover goal (softened): prefer abandoning Python after parity, but deletion is conditional. If even one script is still necessary (launcher piece, validator, migration helper), keep that minimal subset. Delete only what the TS side provably supersedes; no premature removal, no shim for deleted parts.
- Context-cost deep analysis and formal security assessment both deferred to post-completion Phase 5; build-time gating + least-privilege still ship with the code.
- Keep `.pi/extensions/beads-tools` unchanged; new tools copy its gating, use non-colliding names.
- Least privilege **within authority**: grant a subagent only tools it needs *and* is authorized to decide. Ledger writes are Lead-only; functional convenience never grants governance authority. All research subagents get `extensions: []`; `subagentOnlyExtensions` only where functionally needed (worker → aliases + codegraph; others → none).
- Triage agreed: port-first = `ledger_read` + `ledger_task` + `ledger_gate` + `ledger_consult` + `ledger_inner` + `checks`; `ledger_okf`/`ledger_director`/launcher stay in Python until proven otherwise.
- Skill layout agreed: new `.pi/skills/research-ledger/` dir, one file per runbook (payload tables, checkpoint, OKF, consultation, Director); tool snippets point at these, not pasted copies.
- Language preference: TypeScript for all new code; JavaScript or Python only when TS provably can't do it.
- Protect work: commit after each phase (0–5) with phase-scoped messages; never mix with stewardship/ui-verifier changes.

## Phase 0 — Design freeze (before any port)
**Status: INCOMPLETE.** Do not expand implementation beyond the already committed preliminary scaffold until every Phase 0 inventory/design item is resolved. Phase 1 scaffold work began prematurely; it is a prototype, not a phase exit or approval of the full design. Resume at Phase 0, then return to Phase 1 in order.
- [x] Map CLI entrypoints/actions to target tool, Python implementation, initial port/stay disposition, and principal tests in [operation-inventory.md](.pi/skills/research-ledger/references/operation-inventory.md). Source review corrected earlier omissions/misgroupings.
- [ ] Verify/refine the draft per-action schema contracts in [tool-contracts.md](.pi/skills/research-ledger/references/tool-contracts.md) against each Python validator and test; fill exact gate-route/review optionality and refusal cases before Phase 0 exit.
- [x] Agree target Pi-tool surface: ~8 grouped tools with discriminated per-action schemas (over 1-per-op and generic-apply). Detailed design below. Implementation schemas remain pending.
- [x] Agree Lead-only gating pattern: reuse `beads-tools` (`RESEARCH_LEAD_CONFIG` + `RESEARCH_LEAD_PID` + host `MARKER` + `cwd==repo`, `model-only`, `sequential`); no child ledger tools. Initial implementation/tests are in Phase 1.
- [x] Define child extension allowlist in [operation-inventory.md](.pi/skills/research-ledger/references/operation-inventory.md): all seven fixed roles `extensions: []`; worker alone gets model-alias + codegraph as `subagentOnlyExtensions`; others none; no child gets ledger tools. Apply/test the config in the integration phase.
- [x] Agree progressive-disclosure layout: agent.md keeps lifecycle map + must-do rules; `.pi/skills/research-ledger/` carries runbooks; tool descriptions/snippets carry call-time rules. Agent rewrite/tool copy remains Phase 3 work.
- [x] Define narrowed parity/test bar in [conformance-matrix.md](.pi/skills/research-ledger/references/conformance-matrix.md): TS parity only for selected Lead-critical logic; retained Python integration remains tested by Python; all 85 research-ops + 14 OKF suites stay mandatory; stable-vs-dynamic output normalization is explicit.
- [x] Launcher inventory: mapped `init`/`preflight`/`smoke-roster`/`lead` responsibilities and retained them Python/operator-side initially in `operation-inventory.md`; no model-callable bootstrap, model selection, delegation enabling, or attestation.
- [x] Capture JSON oracle vectors in `golden/canonical-json.json` and link source regression `test_ambiguous_and_nonfinite_json_is_refused`.
- [x] Specify TS parity behavior for duplicate-key rejection, non-finite rejection, canonical digest bytes, and `file_sha256` in `conformance-matrix.md`; proving Node matches Python is Phase 2 implementation work.
- [x] Migration inventory: no live `research-projects/*/project-state.json` exists in this checkout; active and historical docs references are listed in `operation-inventory.md`.
- [x] Specify legacy snapshots remain read-only; import only independently verified records via explicit migration receipts/pinned sources; if no migrator exists, retain Python; delete Python files only after proving all callers/dependencies/tests are superseded (`operation-inventory.md`).
- [ ] Phase 0 exit review: ensure the complete operation/action inventory, port-now/stay-Python decisions, tool schemas/authority boundaries, launcher ownership, JSON parity requirements, migration constraints, and parity/test bar are coherent and recorded before Phase 1 resumes.

## Tool-surface design (detailed)
Why not generic `apply` (1 tool): a single `ledger_apply(group, action, payload: object)` keeps the surface tiny but forces `payload` to be a loose object. The model must then recall ~40 payload shapes from prose, and mis-shapes fail late inside Python instead of at tool-call validation. That loses the machine-checking that justifies the port.

Why not 1-per-operation (~40 tools): exact schemas and clear intent, but every tool spec (name + description + snippet + full parameter schema) loads every turn. At ~40 tools this dominates context, raises mis-selection, and complicates maintenance. `beads-tools` proves ~9 tools is comfortable; 40 is a different regime.

Agreed hybrid: 8 grouped tools, each with a discriminated `action` union carrying exact per-action schemas (TypeBox `Union` on `action` literal). Selection picks the domain; validation still enforces the exact shape; `promptSnippet`/`promptGuidelines` on the selected tool expand only its runbook (progressive disclosure).

- `ledger_read` (read-only): `status`, `next`, `show`, `get`, `check-task`, `check-close`, `termination-check`, `progress`. No `op-id`/revision needed except `get` record id. Snippet: read-before-write, HOLD vs gate-HOLD flags, replay/pending-attempt signals.
- `ledger_task` (evidence dispatch): `assess-task`, `issue`, `pin-use`, `mark-ready`, `reserve`, `attach-run`, `launch-unknown`, `prove-non-dispatch`, `hard-cutoff`, `observe-termination`, `record-no-result`, `reconcile-effects`, `result`, `decision`, `record-availability`, `drop-optional`. Per-action schemas pin `beads_task_id`/`assignment_id`/`revision_id`/`attempt_id` echo rules, write/execute `verification` maps, and acceptance-before-closure. Snippet: exact-ID binding, single-submission receipt, late-result and supersede rules.
- `ledger_gate`: `gate-review`, `gate-route`, `reuse-readiness`, `withdraw-stale-review`, `resolve-gate-hold`, `checkpoint-plan`, `checkpoint-gate-hold`, `return-to-implementation`. Schemas enforce manifest/phase/role bindings, `advisor_run_id` uniqueness, route legality, Git `checkpoint` HEAD, and `okf_check` linkage. Snippet: verdict-is-not-route, draft-never-charges, HOLD-checkpoint-before-rereview.
- `ledger_consult`: `configure-consultations`, `reserve-consultation`, `settle-consultation`, `reuse-consultation`, `record-advice-check`, `record-consultation`. Schemas enforce mandatory/exploratory lanes, per-call ceilings, keying (cycle+gate+phase / task id), and contradiction-invalidates-reuse. Snippet: reserve-before-call, settle-before-retry, usable-result bar.
- `ledger_okf`: `begin/prepare/publish/abort-okf-publication`, `check-okf-gate`. Schemas pin `paths`/`request_artifacts`/`publication_id`/`hub_sha256`/writer+reader pins. Snippet: single pending request, stage-then-publish, resume-only-on-exact-bytes, required-reader sufficiency rule.
- `ledger_director`: `record-director-message/delivery/reply/file`, `request-director-stop`, `record-director-stop-reconciliation`, plus project-HOLD `resolve-hold`/`suspend-held`/`open-hold`. Schemas enforce FYI vs DECISION-REQUIRED shapes, scope kinds, options/outcomes, filing markers. Snippet: tag-by-who-acts, park-first-on-stop, filed-reply-before-resume.
- `ledger_inner`: `begin-inner-attempt`, `record-inner-integration`, `record-no-change-interruption`. Schemas pin `start_op_id`/`checkpoint` HEAD and first-parent `src/` proof. Snippet: pin-base-before-edits, one pending attempt, integration-charges-once.
- `checks` (pure validators, no writes): `manifest --artifact-roles --phase-evidence`, `readiness-diff`, `validate-verdict`, `verdict-still-covers`, `check-pool-profile`, `okf-hub-snapshot`, `okf-gate-precheck`, `freshness-flags`. Schemas enforce role maps, phase-evidence fields, and hash maps. Snippet: builder-vs-receipt distinction (precheck is inspection, not authorization).

All 8 share: `model-only` + `sequential` + `beads-tools` gating (config + PID + marker + cwd, refuse otherwise); `state` path resolved from the bound project (no free-floating paths); common envelope (`op-id`, `expected-revision`, `actor`, `reason` on writes; exact replay returns `replayed:true`). Thin-wrapper phase keeps Python as executor behind these same schemas; strangler phase swaps executors module by module with golden-vector dual-run.

## Phase 1 — Extension scaffold (thin wrappers, agreed sequence)
**Status: PRELIMINARY SCAFFOLD ONLY — Phase 0 is not complete.** Existing commits preserve work but do not count as Phase 1 completion. Do not add more wrapper groups or begin logic port until Phase 0 exit criteria are met.
- [x] Create `.pi/extensions/research-ledger-tools/` scaffold (`index.ts`, `gate.ts`, `gating.test.ts`); initial `node --test` gating harness passes. Auto-discovery/strict TS project compilation still needs verification.
- [ ] Thin-wrapper contract: expose each agreed group with exact per-action schemas and correct Python CLI mapping; exercise every action through subprocess fixtures. Current scaffold registers 8 groups but uses generic `input`/`argv`, has unverified action mappings, and is not parity-ready.
- [x] Capture normalized golden traces from the committed Python oracle `3ebe866` under `golden/`: eight existing `test_managed.py` scenarios (cycle charging, gate HOLD, reservation replay/restart, inner charge, wrong IDs, mandatory advice, protocol roles, Director tag) plus exact canonical JSON/hash/rejection vector. Timestamps, temp paths and time-dependent operation fingerprints are normalized; canonical JSON bytes/digest remain exact. Python sources unchanged.
- [x] Add gating-negative tests (wrong/missing PID/config, child env, wrong cwd, missing marker → refused) for pure load/call predicates. Still verify extension registration/execution under Pi in the runtime harness.

## Phase 2 — Lead-critical port only (scope narrowed)
- [ ] Triage `tools/research-ops` into Lead-critical (daily governance: status/next/apply/get, task readiness, gate review/route, consultations, OKF receipts, director records, checkpoints) vs keep-in-Python (reference helpers like `analyze.py`, launcher internals, test scaffolding). Port only the critical set.
- [ ] Canonical-JSON module first: Python-compatible dumps/digest + duplicate-key + non-finite handling, proven against Python vectors. Blocks all later ports.
- [ ] Strangler order: reads → task readiness → gate review/route → consultations → OKF receipts → Director. Each module lands only on byte-identical dual-run; refusal strings stay exact.
- [ ] Port `snapshot_schema` + `project-state.schema.json` validation (duplicate-JSON-keys, non-finite, receipt bindings) — must leave files unchanged on failure.
- [ ] Port `durable` (revision/op-id idempotency, replay, holds) + `evidence` tables.
- [ ] Port `task_readiness` + `evidence` dispatch actions — split: (a) `assess-task` + `check-task`; (b) brief chain `issue`/`pin-use`/`mark-ready`/`reserve`; (c) run chain `attach-run`/`launch-unknown`/`prove-non-dispatch`/`hard-cutoff`/`observe-termination`/`record-no-result`/`reconcile-effects`; (d) outcome chain `result`/`decision`/`record-availability`/`drop-optional`. Each sub-chain lands with its own dual-run before the next starts.
- [ ] Port `gates` + `readiness` + `gate_artifacts` + `gate_checkpoints` — split: (a) `gate-review` intake (manifest/role/Advisor-run binding); (b) `gate-route` legality + charges + stage moves; (c) `readiness`/`reuse-readiness` with baseline/log/diff proof; (d) `checkpoint-plan`/`checkpoint-gate-hold` Git ancestry + byte checks; (e) `withdraw-stale-review`/`resolve-gate-hold`/`return-to-implementation`.
- [ ] Port `inner_attempts` (begin/settle, charge-once rule) as one unit.
- [ ] Port `consultations` — split: (a) `configure`/`reserve`/`settle` with lane budgets; (b) `reuse` + `record-advice-check` + `record-consultation` with contradiction bar.
- [ ] Port `knowledge` + `hub_publication` — split: (a) staged `begin`/`prepare`/`publish`/`abort` with resume-on-exact-bytes; (b) `check-okf-gate` with publication/snapshot/reader-sufficiency binding.
- [ ] Port `director` — split: (a) `message`/`delivery`/`reply`/`file` with scope/option shapes; (b) `stop`/`stop-reconciliation` + `resolve-hold`/`suspend-held`/`open-hold` with resource/stop preconditions.
- [ ] Port only `checks.py` `manifest`, `validate-verdict`, `verdict-still-covers`, and `freshness-flags`; keep OKF prechecks, pool-profile comparison, and the `research.py` launcher Python/operator-side as listed in the operation inventory.
- [ ] Each module lands with ported unit tests; no module is declared done while Python and TS disagree on any fixture.

## Phase 3 — Prompt encoding with progressive disclosure
- [x] Create `.pi/skills/research-ledger/`: `SKILL.md` plus `payload-tables.md`, `checkpoint-runbook.md`, `okf-publication.md`, `consultation-accounting.md`, `director-runbook.md`; files are concise and link to needed details.
- [ ] Rewrite `.pi/agents/research-lead/agent.md` — split: (a) keep lifecycle map + non-negotiables + authority boundaries; (b) replace README links with skill refs; (c) add tool-selection guidance per domain (which of the 8 tools for which job).
- [ ] Tool descriptions per group: write `description` + `promptSnippet` + `promptGuidelines` for each of the 8 tools from the detailed design; review each for call-time-only content (no global rules duplicated).
- [ ] Measure system-prompt size before/after; budget deltas explicitly (full README paste is rejected as the default).

## Phase 4 — Conformance + rollout
- [ ] Port test suites — split per file: `test_ledger` (structure/idempotency), `test_managed` by area (cycle/charging, task dispatch, gates/HOLD, consultations, OKF, Director, checkpoints), `test_pi_bootstrap` (launcher/binding), `test_snapshot_schema` (schema edge cases). Keep Python green until each area's TS counterpart passes.
- [ ] Dual-run — split per module in strangler order (reads → task → gate → consult → OKF → Director); each module needs byte-identical receipts + refusal strings before the next starts. Document any intentional migration delta per module.
- [ ] Migration plan for existing `project-state.json` files (read-only legacy + explicit reconcile, no silent rewrite).
- [ ] Cutover precondition: TS parity suite covers every selected port-now behavior and every retained Python-backed tool has wrapper integration coverage; all 85 Python research-ops + 14 Python OKF tests remain green; `tsc` + Beads adapter checks green; no open ported-slice parity gaps.
- [ ] Cutover (conditional): delete only what TS provably supersedes. Retain any still-necessary Python script as a minimal subset; update references for removed parts only (`README.md`, `blueprint-v1.md`, audit/progress docs, `research-lead/agent.md`). Leave unrelated stewardship plans alone.
- [ ] Commit per phase; never mix with stewardship/ui-verifier changes.

## Phase 5 — Post-completion context-cost analysis + improvement
- [ ] Measure live cost: system-prompt bytes, tool-spec bytes, per-turn tokens with the full tool surface loaded.
- [ ] Analyze whether tool-count/runbook size causes truncation, latency, or missed-guidance issues in real sessions.
- [ ] Invest follow-up effort as needed: tighter progressive disclosure (skill refs vs inline), tool grouping/splitting, snippet trimming, lazy loading. Tracker stays open for this after cutover.
- [ ] Post-completion security assessment (deferred per your call): permission review of the new extension surface, Lead-only gating audit (PID/marker/cwd/child-env negatives), tool-exposure review. Build-time gating tests in Phase 1 still ship with the code; this item is the formal assessment afterwards.

## Concerns (why this is risky)
1. **Correctness:** ~3k lines of ledger semantics + 772-line schema. A subtle divergence (idempotency, HOLD vs gate-hold, checkpoint ancestry) silently corrupts research governance.
2. **Duplication:** two implementations of the same state machine must be kept in lockstep or the old one deleted — mid-migration drift is the failure mode.
3. **Context cost:** exposing ~30 tools + full runbook in-brain on every turn is expensive; progressive disclosure must be real (skills/references/tool-time snippets), not a second paste.
4. **Security:** extensions run with full OS perms. Lead-only gating must be tested like `beads-tools`, not assumed.
5. **Scope creep:** "other relevant agents" must stay default-deny. Worker/Advisor/OKF must never write the ledger directly.
