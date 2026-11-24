# Development tracker — Autonomous Research Team for Applied AI

**Authority:** [Blueprint v1.4](blueprint-v1.md); [Beads tool proposal](proposal-for-assignment-management-tools-beads.md) is implementation guidance, subject to the pinned CLI. This file tracks development, not a research project's task backlog or evidence. Record verification against the actual implementation, and do not mark a live-runtime item complete on the strength of a fixture.
** Pi Session ID:** `01a2067b-888d-7468-be97-dfb6fb376f00`

## 1. Foundation and assignment lifecycle

- [x] Preserve the main Pi session as Research Lead and reuse the seven fixed-role definitions and `pi-subagents`. Keep the pool Lead-only, fixed-roster-first, and opt-in; do not add a scheduler or standing role.
- [x] Separate Beads operational state from durable project evidence; link by exact task ID without mirroring the backlog or its dependency graph.
- [x] Implement typed Beads v0.49.6 SQLite tools: create, exact get, combined lexical/structured query, update, guarded close/reopen, dependency management, ready/blocked views. No task deletion or generic executor.
- [x] Test against real disposable Beads databases: closed lookup/query scope, combined filters, planned dependency release, closure after integration/evidence, refusal of an optional drop that would release required work, no fallback on a missing database.
- [x] Add managed project-state initialization, serialized atomic writes, expected revision checks, and durable operation receipts. Keep historical snapshots readable; legacy `advance` is dry-run only.
- [x] Record issued revisions, READY, launch reservations, Pi run references, outcome/termination, effect reconciliation, results, decisions, and availability. Implement exact retrieval and transitive invalidation on supersession. Store facts separately from Lead assertions.
- [x] Test stale/op-ID replay, concurrent reservations, interruption before and after dispatch (simulated observations), hard cutoff vs termination, wrong/late results, real Git checkpoint, and superseded evidence.
- [x] Record seven-dimension readiness and fixed-roster-first routing per meaningful task. Bind Worker/pool dispatch to a current assessment, and require recorded Advisor follow-up for declared material triggers before reassessing READY. Direct work and other fixed-role calls follow the Lead prompt; fixture checks do not enforce host behavior.
- [x] Exercise pinned Pi startup with disposable project bindings: nine tools present in the bound Lead session, absent for an unbound session and an inherited child environment. Verify with the SDK that none appears in the callable-tool registry used by `codemode`. The probes only run from test fixtures; actual child confinement is still open.

## 2. Main-session lifecycle and onboarding

- [x] Implement phase-bound gate review and guarded routes, separate protocol/readiness approvals, no-verdict HOLD, bounded review recovery, cycle authorization/charging, terminal stop vs completed report, and cap/stagnation predicates.
- [x] Exercise project initialization through final report with simulated reviews, including final-cycle achievement and stale manifest refusal.
- [x] Charge cycle 1 on initial planning, not bootstrap or scoping. Test exact replay, a blocked protocol review, and compatibility with snapshots that already consumed cycle 1 at initialization.
- [x] Bind inner-attempt charges to committed implementation changes from a pinned cycle-workspace base. Test replay, interruptions with no integrated change, pending gate refusal, and the inner-attempt cap using disposable Git repositories.
- [x] Add project bootstrap and launcher with explicit SQLite binding, static preflight, and hash-checked operator observations for deployment opt-in. Keep static checks distinguishable from the effective runtime roster.
- [x] Implement manifest hashing, verdict validation, manifest drift review, freshness flags, and OKF gate precheck using existing validators.
- [x] Align the Lead/Worker prompts, bootstrap artifact layout, blueprint implementation pointers, and operations runbook. Verify a fresh bootstrap in an isolated repository.
- [x] Add §12.4 fixture regressions: final-cycle report, in-plan repair vs forbidden replan at the cap, `block` precedence, malformed review with bounded recovery, stale review replacement, and independent work during another assignment's recovery.
- [x] Bind readiness to the approved protocol’s required tests, tested Git baseline, and pinned output evidence. Validate exact readiness reuse evidence and refuse stale coverage in disposable Git fixtures.
- [x] Require bound OKF validator results for managed cycle, report, and declared service-dependent gate inputs. Refuse missing, mismatched, or stale checks in disposable hub fixtures.
- [x] Enforce managed single-writer hub publication: one bound Lead launcher per project, one staged request at a time, an exact base/target ledger checkpoint, and refusal to advance while publication is unresolved. Test local process interruption during publication and recovery; this is not live child confinement or a Git checkpoint.
- [x] Apply the bundled Draft 2020-12 JSON Schema and cross-record checks to managed initialization, reads, startup, and writes. Verify rejection of malformed state, missing validator, ambiguous JSON, and invalid receipt bindings without mutating the snapshot. Legacy snapshots still use their read-only compatibility path.
- [x] Require phase-specific hashed artifact roles, bind the active charter and cycle proposal, distinguish diagnosis-only from complete exit, and check exact hashes in the report verification record and final manifest. Refuse stale or incomplete packages for new reliance. These checks do not establish scientific sufficiency.
- [x] Require verified Git checkpoints for initial planning, gate routes, readiness reuse, and resumption after an automatic gate HOLD. Pin the exact pre-transition ledger, required artifacts, and resolved cycle decision; reject missing bytes, contradictory decisions and divergent checkpoint history. Emergency HOLD still takes effect before Git.
- [x] Expand local §12.4 fixtures for optional timeout versus mandatory gate failure, independent work during a gate-scoped HOLD, bounded inconclusive recovery, early-stagnation routes, required-reader insufficiency/drift, unrun verification and partial delivery, a lost replan acknowledgment after durable save, uncharged plan-change drafts versus once-charged approved replan, untagged Director messages versus non-holding FYI, and wrong assignment/revision IDs. These are disposable local observations, not live-agent evidence.
- [ ] Run the remaining §12.4 scenarios against real persisted runtime artifacts and approved live execution/recovery; retain objective process and effects evidence.
- [x] Record Director FYI, scoped decisions, delivery gaps, replies, and supersession. Require current indexed filings before reliance, a fresh brief at CYCLE_GATE/REPORT_GATE, and resource reconciliation before resuming a resource HOLD. Park immediately on a stop request; record confirmed exit/effect reconciliation separately. Tested with fixture observations, not a live conversation or live process control.
- [x] Document the versioned consultation brief, quality checklist, and evidence-first two-pass procedure for high-risk reviews. Record exact task-linked advice and Lead disposition. The two-pass procedure is prompt/runbook guidance, not an enforced runtime constraint.
- [x] Separate required and exploratory Advisor call allowances; guard reservations with per-call and per-issue limits, record observed and missing usage, and restrict reuse to unchanged exploratory advice without contradictory checks. Verify with simulated results; production measurement and external quota enforcement remain deployment checks.

## 3. Execution and deployment verification

- [ ] In the selected deployment, verify the pinned versions, trust scope, discovery and exclusions, exact provider/model and override source for all seven fixed roles, tool exposure (including indirect calls), fresh context, and response schema behavior. Capture actual smoke-run and inspection artifacts per role.
- [ ] Verify durable dispatch correlation, process exit, and workspace/external effects against real Pi runs. Test host interruption before launch, after launch before recording run ID, after writes, and after integration but before Beads closure. Leave uncertain launches blocked rather than retrying blindly.
- [ ] Verify per-package file/command/network confinement and Worker → architect-only nesting with direct and `codemode` probes. Prompt allowances and an exposure unit test are not OS sandboxing. Do not enable production delegation while these checks are missing.
- [ ] In the approved runtime, verify stage-only OKF writer confinement and exact writer exit/correlation; exercise interruption and recovery. Retain the `okf_publication_recovery` evidence required by the runtime attestation.
- [x] Add a pool-profile comparison check and fixture tests for model drift and indirect delegation. It compares supplied effective capability records; it does not resolve profiles or verify their confinement.
- [ ] Run a single-writer Worker pilot followed by an operator-approved read-only pool pilot. Validate actual resolved profiles, ambiguity refusal, and failure isolation against real launch evidence. Add concurrency only after the single-writer path and required confinement tests pass.

## 4. Scientific evaluation and reporting

- [x] Implement a deterministic reference paired analysis with frozen input hashes, raw CSV and config provenance, seeded uncertainty, limits, and a clearly labeled draft output. Verify with constructed observations; do not report these as an empirical result about models.
- [ ] **Deferred until runtime development has produced useful usage evidence:** choose a Director-authorized real research question, data, experimental budget, and baselines. Preserve raw observations, split development from confirmatory evidence, retain null/negative results, and trace reviewed claims through the final manifest.
- [ ] **Deferred formal system evaluation:** compare variants, repeated runs, consultation quality, and cost/latency against the §12 rubric after actual usage yields a meaningful evidence base. Do not claim effectiveness from development observations or gate approvals alone.

**Sequencing decision:** The Director intends to debug and improve the system through authorized real runtime use rather than requiring a separate scientific pilot before development. Capture operational evidence from those runs where available. This defers, but does not waive, formal scientific/system evaluation before making effectiveness claims; deployment security and resource-authorization gates still apply.

## 5. Deployment recovery and budgets

- [x] Implement local cycle, inner-attempt, review and assignment attempt accounting; distinguish late or unusable output from observed process exit.
- [ ] Verify external quotas and spending coverage on the approved compute/provider setup. Add context/usage accounting and evaluate decision reuse without weakening freshness or review authority.
- [x] Document the deployment sequence, evidence needed for recovery, and the procedure for a missing Beads close. Documentation does not prove execution correlation.
- [ ] Run and revise the incident runbook against the pinned live environment; capture a recovery report and objective exit evidence.

**Local verification:** 85 research-ops Python tests, 14 existing OKF validator tests, 2 native Beads integration tests, and strict TypeScript compilation passed. TypeScript check: `.pi/node_modules/.bin/tsc --noEmit -p .pi/extensions/tests/tsconfig.json` with TypeScript 5.9.3 and `@types/node` 22.19.19. The Python suite includes a real Pi CLI/SDK exposure probe, real Git integration, a process-exec project lock test, a ledger subprocess terminated after its first hub file replacement, and a replan subprocess terminated after durable state save but before its acknowledgment. New fixtures cover uncharged drafts, tag enforcement, and ID binding. Child execution and gate observations remain fixture data. A disposable TypeScript runtime smoke also confirmed workflow transpilation; the repository's launcher integration test still requires its absent `agent-collaboration/code-analysis` project fixtures.

**Deployment constraint:** No `research-projects/` deployment/attestation or operator-approved confinement and pool profile was present in this checkout. No paid or live child runs were launched; deployment smoke, confinement probes, and Worker/pool pilots remain open.

**Next locally:** Reconcile any remaining implementation gaps against current source and add narrowly scoped regressions where local mechanics can substantiate them. Remaining live dispatch, communication, confinement, and recovery scenarios require an approved deployment.

**Next for deployment:** (1) complete the operator-approved model and confinement probes in a disposable deployment, (2) perform the single-writer and approved read-only pool launch/recovery pilots, (3) continue authorized real-use development with operational evidence capture; schedule formal research/system evaluation after sufficient runtime evidence accumulates and before making effectiveness claims.
