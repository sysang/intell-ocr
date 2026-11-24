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
- [ ] Inventory every CLI entrypoint: `ledger.py` (status/next/show/apply/get/check-task/check-close/checkpoint-plan), `checks.py` (manifest/readiness-diff/verdict-still-covers/pool-profile/hub-snapshot/precheck), `research.py` (init/preflight/lead), plus library modules (durable/gates/evidence/task_readiness/consultations/knowledge/hub_publication/gate_artifacts/gate_checkpoints/director/readiness/inner_attempts/snapshot_schema/analyze).
- [ ] Define Pi-tool surface: ~8 grouped tools with discriminated per-action schemas (agreed over 1-per-op and generic-apply). See `Tool-surface design (detailed)` below; exact per-action JSON shapes from README tables; tool `promptSnippet`s carry call-time rules.
- [ ] Define gating: reuse `beads-tools` pattern (`RESEARCH_LEAD_CONFIG` + `RESEARCH_LEAD_PID` + host `MARKER` + `cwd==repo`, `model-only`, `sequential`). Decide which tools (if any) other agents get — default is Lead-only.
- [ ] Child hardening: all research subagents get `extensions: []` (defense in depth — global Lead tools never load in child context even if gating failed). `subagentOnlyExtensions` only where functionally needed: `engineering-worker` → `myteam-aliases` + `codegraph`; `research-advisor`/architects/OKF services → none unless proven (they already have minimal `tools` allowlists). New ledger tools are never listed in any child's `subagentOnlyExtensions`.
- [ ] Define progressive disclosure: agent.md keeps lifecycle map + must-do rules; skill/reference files carry payload tables, checkpoint runbook, OKF publication, consultation accounting, Director runbook; tool `description`/`promptSnippet`/`promptGuidelines` carry call-time rules. No verbatim 218-line paste.
- [ ] Define parity bar: all 85 research-ops + 14 OKF validator behaviors must pass against TS implementation (ported conformance suite), plus `tsc --noEmit` and existing Beads adapter tests.
- [ ] Launcher inventory (folded in) — split: (a) `init` (project layout, Beads DB, config, charter); (b) `preflight` (pins, fingerprints, policy evidence, smoke roster); (c) `lead` (system-prompt appends, extension loading, env wiring, planning-only flags, resume/RPC). Record the TS home for each.
- [ ] JSON parity traps (folded in) — split: (a) duplicate-key rejection vectors; (b) non-finite rejection vectors; (c) canonical digest byte-equivalence (`sort_keys` + separators) + `file_sha256` stability. Node must match Python on all three before any receipt comparison.
- [ ] Migration inventory (folded in) — split: (a) live `research-projects/*/project-state.json` list + versions; (b) docs references to `python -B` (`README.md`, `blueprint-v1.md`, audit/progress docs, agent prompts); (c) legacy-snapshot read-only rule + reconcile path. Deletion only after cutover precondition holds.

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
- [ ] Create `.pi/extensions/research-ledger-tools/` with `index.ts` + `package.json` if needed; verify auto-discovery; add `tsconfig` + `node --test` harness entries.
- [ ] Thin wrappers first (no logic port): one wrapper per agreed group (`ledger_read`, `ledger_task`, `ledger_gate`, `ledger_consult`, `ledger_okf`, `ledger_director`, `ledger_inner`, `checks`) calling the Python CLI via subprocess with the same JSON schemas the port will keep. Start with read-only `ledger_read` (`status`/`next`) to validate gating, schema plumbing, and harness, then add groups in strangler order.
- [ ] Capture golden vectors from Python now (10 agreed: 5 happy + 5 refusal/HOLD) as `golden/` input+output+revision JSON; freeze Python (`tag oracle`) until capture is done.
- [ ] Add `route-governor`-style tests for gating (wrong PID, child env, wrong cwd, missing marker → refused).

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
- [ ] Port `checks.py` builders/validators and `research.py` init/preflight (lead launcher stays operator-side).
- [ ] Each module lands with ported unit tests; no module is declared done while Python and TS disagree on any fixture.

## Phase 3 — Prompt encoding with progressive disclosure
- [ ] Create `.pi/skills/research-ledger/` — split one file per runbook: `payload-tables.md` (all action shapes), `checkpoint-runbook.md`, `okf-publication.md`, `consultation-accounting.md` (brief + checklist), `director-runbook.md`. Each stays under ~100 lines with links, not prose dumps.
- [ ] Rewrite `.pi/agents/research-lead/agent.md` — split: (a) keep lifecycle map + non-negotiables + authority boundaries; (b) replace README links with skill refs; (c) add tool-selection guidance per domain (which of the 8 tools for which job).
- [ ] Tool descriptions per group: write `description` + `promptSnippet` + `promptGuidelines` for each of the 8 tools from the detailed design; review each for call-time-only content (no global rules duplicated).
- [ ] Measure system-prompt size before/after; budget deltas explicitly (full README paste is rejected as the default).

## Phase 4 — Conformance + rollout
- [ ] Port test suites — split per file: `test_ledger` (structure/idempotency), `test_managed` by area (cycle/charging, task dispatch, gates/HOLD, consultations, OKF, Director, checkpoints), `test_pi_bootstrap` (launcher/binding), `test_snapshot_schema` (schema edge cases). Keep Python green until each area's TS counterpart passes.
- [ ] Dual-run — split per module in strangler order (reads → task → gate → consult → OKF → Director); each module needs byte-identical receipts + refusal strings before the next starts. Document any intentional migration delta per module.
- [ ] Migration plan for existing `project-state.json` files (read-only legacy + explicit reconcile, no silent rewrite).
- [ ] Cutover precondition: ported suite covers all 85 research-ops + 14 OKF behaviors; `tsc` + Beads tests green; zero open parity gaps.
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
