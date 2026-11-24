# Blueprint-to-Implementation Audit

## Tracking metadata

- **Audit start (UTC):** 2026-11-24T06:10:26Z
- **Design authority:** `blueprint-v1.md`, version 1.4 (working authority named by the document).
- **Implementation tracker:** `todos.md` (tracker claims are leads, not proof).
- **Project root:** branch `main`, HEAD `12f728f9b8501ca3ca1253d336a86af442a31753`; pre-existing working-tree changes: `development-progress-report.md`, `todos.md`.
- **Pi configuration checkout (`.pi`):** branch `intell-ocr`, HEAD `4a9570e1faef23dd9c08ba61a5e2b0d66509b45d`; pre-existing working-tree changes: `package.json`, `package-lock.json`.
- **Audit report:** new file `blueprint-implementation-audit.md`; not committed as part of either initial checkpoint above.
- **Audit/strategy-update checkpoint captured:** 2026-11-24T07:12:31Z.
  - Project root: branch `main`, HEAD `d345f942feb8fd34ef681c20dfebdd242026a58b`; working tree has modified `todos.md` and untracked `blueprint-implementation-audit.md`.
  - `.pi`: branch `intell-ocr`, HEAD `18f4c327b6aed209ee153524928391910bd9cabb`; working tree clean.
  - No commits were created for this audit report or sequencing update.

## Method and decision rules

The review proceeds **sequentially by numbered top-level blueprint section (1 through 15)**. Each section is one audit item and will be recorded as reviewed before the next item begins. Within each item, the report will enumerate its numbered subsections and material requirements so that a section-level completion marker never hides partial specification coverage.

For each requirement, distinguish:

- **Implemented & verified:** executable component/test evidence covers the stated behavior; static source presence alone is insufficient for behavioral claims.
- **Prompt-encoded:** instruction exists in a targeted role prompt, but is not independently enforced by application/runtime policy.
- **Partial:** some but not all required clauses have implementation/evidence.
- **Not implemented:** no adequate source or test evidence found.
- **Unverified:** source/configuration exists, but the required live/deployment/empirical evidence is absent.
- **Not applicable / illustrative:** blueprint content is explanatory rather than an acceptance requirement.

Evidence citations identify concrete files, tests, schemas, or runbook sections. A passed fixture does not establish live child behavior, provider resolution, sandboxing, scientific validity, or external resource controls. This audit checks implementation and encoding; it does not run live/paid child agents or claim deployment authorization.

CodeGraph is not initialized for this checkout, so source inspection is by direct file inventory, search, and file reads. This is recorded as a tooling limitation, not evidence of missing implementation.

## Sequential review tracker

| Audit item | Blueprint scope | Review status |
|---|---|---|
| 1 | System objectives and design principles (§1) | **REVIEWED — PARTIAL IMPLEMENTATION** |
| 2 | Architectural decomposition (§2) | **REVIEWED — PARTIAL IMPLEMENTATION; LIVE PATHS UNVERIFIED** |
| 3 | Research Lead specification (§3) | **REVIEWED — PARTIAL; READINESS/CONSULTATION RULES INCOMPLETE** |
| 4 | Research Advisor specification (§4) | **REVIEWED — CONTRACT/VALIDATION PRESENT; LIVE REVIEWS UNVERIFIED** |
| 5 | Research workflow design (§5) | **REVIEWED — GATE SKELETON PRESENT; RESEARCH STAGES/ARTIFACTS INCOMPLETE** |
| 6 | Advisor consultation and context engineering (§6) | **REVIEWED — BASIC PROMPT DISCIPLINE; PACKAGE/BUDGET SYSTEM MISSING** |
| 7 | Research artifacts, knowledge, and memory (§7) | **REVIEWED — PROJECT SCAFFOLD/MANIFEST HELPERS; KNOWLEDGE AND CLAIM TRACEABILITY INCOMPLETE** |
| 8 | Host orchestration, state, and execution contracts (§8) | **REVIEWED — STRONG LOCAL LEDGER; RUNTIME/GOVERNANCE GAPS REMAIN** |
| 9 | Scientific rigor and evaluation policy (§9) | **REVIEWED — REFERENCE ANALYSIS ONLY; EMPIRICAL PROTOCOL/RESULTS ABSENT** |
| 10 | Pi implementation architecture (§10) | **REVIEWED — SOURCE/TOOLS PRESENT; RUNTIME ASSURANCE INCOMPLETE** |
| 11 | Agent prompts and contracts (§11) | **REVIEWED — PROMPTS SUBSTANTIALLY MATCH; READINESS/DELEGATION/SECURITY GAPS REMAIN** |
| 12 | Evaluating the research-agent system (§12) | **REVIEWED — FIXTURE REGRESSIONS PARTIAL; NO EMPIRICAL SYSTEM EVALUATION** |
| 13 | Implementation roadmap (§13) | **REVIEWED — NO MILESTONE EXIT CRITERIA FULLY EVIDENCED** |
| 14 | Worked example (§14) | **REVIEWED — ILLUSTRATIVE; NO EXAMPLE STUDY EXECUTED** |
| 15 | Final design decisions (§15) | **REVIEWED — DESIGN CHOICES MOSTLY REFLECTED; TARGET NOT COMPLETE** |

---

## Audit item 1 — System objectives and design principles (§1)

**Review completed:** 2026-11-24 (item 1; before item 2). **Item verdict: PARTIALLY IMPLEMENTED / ENCODED; not fully verified.** The role split, host-led lifecycle, evidence checks, and stage-gate machinery are substantially represented in prompts and local components. The prompt layer remains bypassable by design; live role execution has not been observed. The broad task-readiness assessment, project-wide external resource budgets, and required gate/cycle Git checkpoint enforcement are notable gaps.

### §1.1 Mission and role split

| Specification | Finding | Evidence / limitation |
|---|---|---|
| Human director defines direction, goals, constraints, and feedback; Lead owns research lifecycle and deliverables. | **Prompt-encoded.** | `.pi/agents/research-lead/agent.md` assigns planning, investigation, implementation, evaluation, analysis, and reporting to the host Lead; its director-communication rules reserve authority decisions for the human. No live project is available to verify behavior. |
| Advisor supplies methodological/intellectual review; Worker performs only bounded Lead-assigned implementation and returns evidence; neither owns research decisions. | **Prompt-encoded with partial structural support.** | `.pi/agents/research-advisor/agent.md` is read-only, prohibits execution/delegation, and limits gate verdicts to explicit Lead requests. `.pi/agents/engineering-worker/agent.md` states allowed-path and result-contract boundaries. `tools/research-ops/evidence.py` separately records brief, result, Lead decision, and availability. Actual agent runs and OS-level enforcement remain unverified. |
| Lead is the main Pi host; Advisor and Worker are subagents; no separate Lead child or lifecycle workflow engine is required. | **Implemented as the documented launch shape.** | `tools/research-ops/research.py` starts Pi with `--append-system-prompt` for the Lead, gates delegation behind an operator attestation, and the `.pi/settings.json` excludes the Lead definition from child discovery. No separate lifecycle script is present; this conforms to the blueprint. Actual seven-agent discovery/run behavior is unverified. |
| Human escalation is reserved for authority, missing essential information, major objective changes, and unresolved critical issues. | **Prompt-encoded / behavior unverified.** | Lead prompt contains authority tags, stop handling, ambiguity clarification, and escalation guidance. No real director interaction was exercised. |

### §1.2 Core principles

| Principle | Verdict | Evidence and specification-level assessment |
|---|---|---|
| **P1 — Fixed roster, flexible capacity; pool only outside all seven scopes, operator-approved, Lead-only, no role substitution.** | **Partial; largely prompt-encoded; live enforcement unverified.** | Seven fixed names are enumerated in `tools/research-ops/evidence.py` and smoke-roster validation in `research.py`; `.pi/settings.json` excludes the Lead. The Lead prompt directs fixed-roster-first and operator-approved pool use. `checks.py check-pool-profile` compares supplied approval/observation, and assignment records require routing rationale for a non-fixed assignee. These do not resolve the runtime profile or enforce all caller/delegation edges. No live pool qualification was performed. |
| **P2 — Lead remains accountable for every deliverable; Advisor advice does not transfer ownership.** | **Prompt-encoded with local acceptance separation.** | Lead, Advisor, and Worker prompts state the ownership boundary. `evidence.py` separates Worker results from Lead decisions/availability and validates accepted outputs. No live delivery was accepted in this audit. |
| **P3 — Host-led dynamic dual loop, bounded loops, mandatory reviews/termination, direct Advisor invocation.** | **Partial: prompt plus guarded state transitions, not non-bypassable runtime policy.** | Lead prompt describes the loops and gate behavior. `tools/research-ops/gates.py` validates phase-bound reviews and legal routes; `ledger.py` tracks cycle and attempt predicates. Consistent with the blueprint’s explicit caveat, host instructions and these managed routes do not prevent every direct host action; no permission/policy extension provides hard gate enforcement. |
| **P4 — Evidence, tests, observations, and reproducibility outweigh Advisor agreement.** | **Partial implementation / encoded.** | Gate manifests and verdict validation are in `gates.py`/`checks.py`; `evidence.py` checks source pins, evidence refs, verification results, artifact hashes, and accepted Git checkpoint contents. Prompts distinguish review approval from proof. These checks establish structure and provenance, not whether scientific claims are true; live experiment evidence is absent. |
| **P5 — Readiness and uncertainty assessment precede meaningful work; unresolved uncertainty triggers consultation.** | **Not fully encoded; material gap.** | The Lead prompt has stage readiness approvals and requires assignment `READY` before dispatch, while `evidence.py` records a readiness basis for an exact brief. However, `.pi/agents/research-lead/agent.md` does not encode the blueprint’s seven-dimension task-readiness assessment or READY/INVESTIGATE/CONSULT/BLOCKED classification for every meaningful task. The assignment `mark-ready` record is not a substitute for that assessment. |
| **P6 — Independent Advisor verdict at PLAN, inner-exit, cycle, and report gates; per-attempt checks are not gates.** | **Partial implementation / prompt-encoded; live use unverified.** | The Lead prompt distinguishes per-attempt checks from phase-specific gate reviews. `gates.py` accepts only phase-compatible, manifest-bound review records and guards routes; local fixture tests cover gate flows. A recorded Advisor run ID is not independent proof of a real child execution, and no live gate review was run. |
| **P7 — Focused, decision-oriented briefs with primary evidence references rather than full histories.** | **Prompt-encoded; no end-to-end quality evidence.** | Lead and Advisor prompts request focused questions, cited artifacts, and bounded evidence expansion. The checked-in code does not construct or semantically validate every consultation packet, and no consultation-quality experiment was run. |
| **P8 — Preserve null/negative results, unresolved questions, failures, and contradictions.** | **Prompt-encoded with partial record support.** | Lead reporting instructions require limitations/negatives; assignment results have gaps, statuses, deviations, and verification fields. There is no general experiment-result store that by itself enforces preservation of all null/negative/contradictory scientific observations. No empirical study was run. |
| **P9 — Durable git checkpoints at gate decisions, cycle boundaries, and accepted workspace-changing deliveries; immutable history and manifest hashes.** | **Partial.** | Lead prompt/runbook instruct checkpoint commits; manifest tools hash artifacts; accepted workspace-changing assignment availability requires an integrated full Git commit and verifies committed artifact bytes in `evidence.py`. There is no code path enforcing a commit at every gate decision/cycle boundary, nor a no-history-rewrite policy enforced by the toolset. Pi runtime retention is explicitly not the long-term source of truth. |
| **P10 — Explicit per-project compute/model/iteration/external-action budgets; director alone controls cessation; HOLD at project-budget exhaustion.** | **Partial; external budgets are not implemented.** | `durable.py`, `ledger.py`, and `gates.py` track outer cycles, inner attempts, gate retries, and assignment attempts/deadlines; the Lead prompt says human-held stop authority takes precedence. The managed budget currently includes outer cycles, not project-level spend/tokens/compute/external-action accounting. `todos.md` lists external quota/spending verification as open. |

**Item 1 disposition:** Review complete. Section 1 is **not fully implemented**. The core role/authority model is encoded, and some lifecycle/evidence mechanics are guarded in local tools. Readiness assessment is materially incomplete; P9 gate/cycle commit enforcement and P10 external resource accounting are missing; P1/P3/P6 enforcement and all runtime behavioral claims remain unverified or instruction-level.

**Next item:** §2, Architectural decomposition.

---

## Audit item 2 — Architectural decomposition (§2)

**Review completed:** 2026-11-24 (item 2; after item 1 and before item 3). **Item verdict: PARTIALLY IMPLEMENTED / ENCODED; operational exit criteria not met.** The repository contains the specified host prompt, two research-role subagent definitions, three consultant definitions, two OKF service definitions, settings exclusion, and supporting Beads/ledger tools. Role boundaries are strongly expressed in prompt/frontmatter and partly represented in state tooling. Runtime discovery, effective permissions, and nested Worker→architect reachability have not been demonstrated.

### §2.1 Pi-native logical architecture

| Specification | Finding | Evidence / limitation |
|---|---|---|
| Human director → main Pi Lead host; Lead calls Advisor for advice/review and Worker for bounded implementation; Lead verifies/accepts and owns next-state routing. | **Architecture encoded; behavior partially supported.** | `.pi/agents/research-lead/agent.md`, `research-advisor/agent.md`, and `engineering-worker/agent.md` define the roles; `tools/research-ops/research.py` appends the Lead prompt and loads bound Beads tools; `evidence.py` records brief/result/decision/availability separately. No live child calls or delivery acceptance were observed. |
| Pi Subagents supplies child sessions and run handling, not the research-stage state machine. | **Matches implementation boundary.** | Lifecycle state is in `tools/research-ops/{durable.py,ledger.py,gates.py}`; no separate workflow engine/script is present. Pi child behavior is not tested live. |

### §2.2 Deliverables and startup

| Specification | Finding | Evidence / limitation |
|---|---|---|
| Lead host prompt, Advisor/Worker agent definitions, three architects, two OKF services, and Lead exclusion from child discovery. | **Present in source/configuration.** | All seven fixed-role directories and `agent.md` files are present under `.pi/agents/`; `.pi/settings.json` excludes `agents/research-lead`. `tools/research-ops/research.py` checks the seven canonical definitions and installed pins in static preflight. This does not prove runtime discovery or resolved agent configuration. |
| Start from repository root with Research Lead prompt appended; require Subagents loaded for delegation. | **Launcher path implemented; deployment path conditional.** | `research.py lead` appends `.pi/agents/research-lead/agent.md` and defaults to planning-only; `--enable-delegation` requires verified smoke attestation. The launcher’s checks and documentation do not establish that the chosen deployment actually loaded the intended Subagents extension/provider. |
| Research records and execution artifacts live in a versioned per-project workspace, not in extra agent definitions or a lifecycle script. | **Bootstrap layout partially implements this.** | `research.py init` creates a project state, charter, OKF hub index, `src/`, `literature/`, `manifests/`, `reports/`, and `runtime/` paths. No initialized research project or its populated artifact corpus exists in this checkout; full §7 layout is audited in item 7. |

### §2.3 Host-led orchestration and review enforcement

| Specification | Finding | Evidence / limitation |
|---|---|---|
| Lead runs readiness/consultation/lifecycle; Advisor receives focused, fresh-context, read-only reviews and structured decisions; Lead verifies evidence. | **Prompt-encoded and partially guarded.** | Lead and Advisor prompts express these obligations; Advisor declares `defaultContext: fresh`, read-only tools, bounded evidence expansion, and the §4.4 JSON contract. `gates.py` validates gate/phase/manifest/verdict shape and legal routes. Actual child context, response schema behavior, and primary-artifact access remain unverified. |
| Monitor each launched child, poll bounded work, reconcile run/session evidence, record failures, and smoke-test all seven fixed roles before research; verify pool candidates each time. | **Prompt and preflight/attestation schema exist; operational behavior unverified.** | Lead prompt and `tools/research-ops/README.md` prescribe these steps. `research.py verify_smoke` validates a supplied seven-role attestation and hashes, but does not launch jobs or verify that operator assertions are truthful; no attestation exists here. |
| Gate instructions are not hard enforcement against direct host actions; a permission/policy extension would be needed for non-bypassable control. | **Explicitly acknowledged; no hard gate extension found.** | Blueprint and Lead prompt both state the limitation. `gates.py` protects transitions made through the ledger only. This is not a defect against the stated initial architecture, but it means policy-level guarantees must not be described as runtime-enforced. |

### §2.4 Role separation, specialist and knowledge services, pool, permissions

| Specification | Verdict | Evidence and limitation |
|---|---|---|
| Lead owns research decisions, implementation assignment/verification/acceptance, reporting, and human escalation. | **Prompt-encoded, with assignment acceptance mechanics.** | Lead prompt contains the role/authority boundary and director communication contract; Worker and Advisor prompts deny decision/acceptance ownership. `evidence.py` separates result from Lead decision and availability. No live lifecycle behavior was observed. |
| Advisor is a read-only methodological reviewer and sole source of required gate verdicts; no write/edit/shell/delegation access. | **Declared tool boundary present; effective boundary unverified.** | `.pi/agents/research-advisor/agent.md` declares only `read, grep, find, ls`, fresh context, and no delegation; its prompt restricts verdicts to explicit Lead gate requests. No runtime callable-tool or indirect-access probe was performed. |
| Worker is a bounded writer, uses the two required skills, has nested delegation depth 2, and may consult only the three architects—not the Advisor or Lead. | **Prompt/frontmatter present; nested-call enforcement unverified.** | Worker frontmatter declares `edit/write/bash/subagent`, the two skills, `allowNestedSubagents: true`, `maxSubagentDepth: 2`, and fresh context. Prompt prohibits Advisor/Lead delegation and permits only three architect consultants. The actual Worker→each-architect dry runs and denial of all other edges have not been executed; tool/path declarations do not prove OS confinement. |
| Three specialists remain read-only, caller-agnostic domain advisors and do not make decisions, write, or gate. | **Definitions present; call-site behavior unverified.** | `harness-architector`, `backend-architector`, and `frontend-architector` exist and declare `tools: read`; their prompts prohibit edits/execution/authorization and describe their domain scopes. Their actual discovery from a nested Worker context has not been proven. |
| `okf-reader` retrieves attributable evidence/gaps read-only; `okf-writer` performs bounded OKF maintenance but cannot commit or alter project state/source. Lead is sole invoker and verifies outputs. | **Service contracts present; exclusivity and sandbox boundaries prompt-level.** | `.pi/agents/okf-reader/agent.md` and `okf-writer/agent.md` contain explicit result/authority/workflow contracts; reader declares no delegation/read-only acceptance and writer has edit/write tools but says no commits or `src/`/state work. Lead prompt calls itself sole invoker. No runtime check proves that other children cannot invoke these agents or that writer tool access is OS-confined. Agent-local OKF spec trees and validators exist. |
| General pool is distinct from fixed roster, opt-in, Lead-only, and narrowly authorized per assignment. | **Partial implementation.** | `evidence.py` recognizes the seven fixed roles and requires an explicit routing reason for non-fixed assignments; `checks.py pool_profile` compares operator-approved and observed profile fields and rejects selected prohibited indirect tools. The comparator explicitly does not discover or verify runtime confinement. No approved profile or pool run exists. |
| Pi tool allowlists do not imply OS-level isolation. | **Correctly documented; isolation not established.** | The blueprint, Worker/OKF prompts, and operations README explicitly disclaim OS confinement. Runtime denied-path/command/network probes remain open in `todos.md`. |

**Item 2 disposition:** Review complete. The static deliverables and intended separation are substantially present. The system does **not** yet meet the operational exit claims for seven-role discovery/resolution, effective permission boundaries, Worker→architect discovery, exclusive Lead invocation of knowledge services, or pool confinement. These remain prompt-level or unverified, as explicitly distinguished by the blueprint and deployment runbook.

**Next item:** §3, Research Lead specification.

---

## Audit item 3 — Research Lead specification (§3)

**Review completed:** 2026-11-24 (item 3; after item 2 and before item 4). **Item verdict: PARTIALLY IMPLEMENTED; critical behavioral rules are not fully encoded.** The assignment specification, Worker routing/acceptance mechanics, cycle ledger, and reference analysis helper provide useful implementation scaffolding. The Research Lead prompt does not include the mandated readiness assessment, uncertainty taxonomy, or most consultation triggers; there is no durable readiness classification for every meaningful task. Model competence and research behavior cannot be verified without a live research exercise.

### §3.1 Primary capabilities

| Capability | Finding | Evidence / limitation |
|---|---|---|
| Research framing: questions, hypotheses, objectives, success criteria, bounded packages. | **Role objective encoded; actual planning output absent.** | Lead prompt asserts ownership and the bootstrap creates a charter/planning workspace, but no research plan or gate-reviewed research charter exists in this checkout. |
| Technical investigation: search/retrieve/synthesize papers, docs, repositories, benchmarks, implementations. | **Partially supported, not end-to-end.** | Host has local inspection tools and `okf-reader` is a retrieval service for a supplied local bundle. The default launcher is planning-only and omits extensions/MCP; no trusted literature/search tool or real literature review was found in the research-ops implementation. External-source investigation capability is not verified here. |
| Software engineering: specify bounded packages; route implementation to Worker; Lead verifies and accepts. | **Strong local assignment scaffold; live behavior unverified.** | Worker role prompt; `evidence.py` brief schema (scope, deliverable, criteria, exclusions, source versions, path/command/tool grants, attempt/time budgets); result/decision/availability phases; and Beads adapter. These implement the record/acceptance mechanics, not the §3.5 delegation decision itself. |
| Experimental methodology: baselines, confounds, controls, runs, measurements. | **Prompt-level responsibility; no study execution.** | Lead/Advisor prompts and blueprint templates describe methodology; no experimental runner or empirical study is present. The pair-analysis helper is downstream analysis support, not a methodology designer. |
| Scientific analysis: interpret qualitative/quantitative evidence, alternatives, uncertainty. | **Narrow reference component plus prompt-level responsibility.** | `tools/research-ops/analyze.py` implements seeded paired-bootstrap analysis with frozen inputs and limitations. It is a narrow deterministic helper; broad qualitative/statistical analysis and model performance are unverified. |
| Technical reporting: reproducible report linking question, methods, observations, results, conclusions, limitations. | **Prompt/workspace shape only; no final research report.** | Lead prompt requires executive and technical reporting with limits/negatives; bootstrap creates `reports/`. The available `analyze.py` output is expressly a draft, not a final report or Advisor verdict; no completed report exists. |

### §3.2 Mandatory task-readiness assessment

| Required clause | Finding | Evidence / limitation |
|---|---|---|
| Before every meaningful task, assess problem understanding, information, methodology, technical competence, verification, risk, and unresolved uncertainty. | **Not implemented in the Lead prompt or managed project-state schema.** | Search of `.pi/agents/research-lead/agent.md` finds stage-readiness approval and assignment readiness only, not the seven-dimension check. `project-state.schema.json` has no general task-readiness record. |
| Classify each task READY / INVESTIGATE / CONSULT / BLOCKED and record evidence in active state. | **Not implemented as specified.** | `evidence.py mark-ready` records a basis for an issued Worker/pool brief; it does not record these four dispositions or make readiness a general task prerequisite. No task-readiness classifier/record was found. |
| CONSULT directly invokes Advisor; BLOCKED pauses/escalates; no arbitrary numeric confidence. | **Partial prompt encoding.** | Gate-review mechanisms directly bind reviews to Advisor run IDs; Lead prompt contains authority-boundary/hold instructions. It lacks the §3.2 classification and confidence guidance for routine meaningful work, so the prescribed routing is not fully operationalized. |

### §3.3 Uncertainty classification

**Finding: Not encoded as the blueprint’s working taxonomy.** The Lead prompt does not enumerate the seven categories and responses: factual→primary source; conceptual/methodological/interpretive/strategic→Advisor as appropriate; technical→inspect/test; resource→calculate/revise. Some adjacent rules exist in the Advisor/Worker prompts, readiness-gate machinery, and resource-cycle counters, but these do not implement the Lead’s uncertainty classification or consultation decision record. The exact taxonomy therefore remains a specification gap.

### §3.4 Mandatory consultation triggers

| Trigger | Finding |
|---|---|
| 1–9: unclear question, unjustified theory, materially different methods, no credible evaluation, contradictory evidence, results undermine hypothesis, repeated conceptual failures, highly interpretive conclusion, scope change invalidating decisions. | **Not found as an explicit trigger list or equivalent durable trigger policy in the Lead prompt or project-state schema.** Some are plausible Advisor consultation topics in the Advisor prompt, but that prompt defines how the Advisor reviews a request, not when the Lead must make one. No trigger exercises were run. |
| 10: required stage-review gate. | **Partially implemented.** Lead prompt and `gates.py` require managed gate review/route records, subject to the §1/§2 caveat that direct host actions are not application-blocked. No live Advisor review was executed. |
| Never bypass a trigger/gate based on self-reported confidence; create focused packet, review advice, record decision; ask human if blocked. | **Partially prompt-encoded.** Gate no-verdict handling, manifest validation, and director escalation exist in prompt/tooling; material-trigger routing outside gates has no complete implementation. |

### §3.5 Delegate concrete, self-contained work

| Specification | Verdict | Evidence and limitation |
|---|---|---|
| Meaningful READY work that is easy to hand off must be delegated when a suitable authorized role exists within budget; split independently verifiable work. | **Not fully encoded/enforced.** | The Lead prompt says fixed-roster-first and describes dispatch, but does not contain the blueprint’s mandatory-delegation decision rule. The project state has no general assignment-vs-direct-work readiness record. A task can remain in the host without a machine-visible rationale. |
| Classify fixed roles first; route covered work to that role; only work outside all seven may use pool; split mixed work; unavailable fixed role does not permit pool substitution. | **Partially prompt-encoded, not mechanically routed.** | Lead prompt says use fixed roster first/no substitute. `evidence.py` assignment issue supports Engineering Worker or a non-fixed pool assignee with routing reason, but does not classify the work itself or enforce role matching across all seven. Advisor/OKF/architect tasks use separate `subagent` calls outside this ledger. No routing cases were exercised live. |
| Record why no fixed role covers pool task and why meaningful work remains direct; retain authority with Lead. | **Lead authority encoded; rationale coverage incomplete.** | Pool assignment requires `routing_reason`; Worker/result decisions are separately recorded. No durable record type was found for a decision to keep a meaningful task with the Lead, and the prompt does not require a reason for every such case. |
| Operator-approved canonical pool profile tied to effective capabilities; assignment separately narrows reads, writes, commands, tools, external actions; pool cannot govern/commit/delegate/decide/contact human. | **Partial data validation; runtime boundary unverified.** | `checks.py pool_profile` compares operator and observed name/hash/model/override/tool/indirect-tool/endpoint records; `evidence.py` stores assignment path/action/tool/time budgets and requires a routing reason; Worker prompt denies governance powers. The comparison is explicitly not runtime discovery/sandbox enforcement; no approved profile or actual pool profile exists. |
| Use Beads for operational task and project ledger for execution/evidence; no pool substitute for required fixed-role call; dependency-scoped recovery. | **Mechanics implemented and fixture-tested; end-to-end dispatch unverified.** | Beads adapter and ledger links exact task IDs and result/decision/integration; tests use real disposable Beads SQLite and simulate Pi receipts. No real pool/Worker assignment or recovery was run. |
| `codemode` batching/model execution is permitted only within assignment authorization; QuickJS sandbox does not restrict called tools/models or roll back side effects. | **Documented boundary; assignment-level runtime enforcement not verified.** | README and blueprint state tool side effects and profile limitations; pool comparator inventories indirect tools/endpoints. No direct/`codemode` permission probes were run. |

**Item 3 disposition:** Review complete. The Lead’s general responsibilities and implementation-assignment infrastructure exist, but §3 is **not fully implemented**. The key conformance gap is the missing all-task readiness/uncertainty mechanism and missing explicit consultation triggers; the mandatory-delegation and no-delegation rationale rules are also absent/incomplete. Capability quality requires live evidence and cannot be inferred from the role prompt.

**Next item:** §4, Research Advisor specification.

---

## Audit item 4 — Research Advisor specification (§4)

**Review completed:** 2026-11-24 (item 4; after item 3 and before item 5). **Item verdict: SUBSTANTIALLY ENCODED; PARTIALLY IMPLEMENTED AND NOT BEHAVIORALLY VERIFIED.** The Advisor definition contains the scientific reviewer mission, consultation modes, critical-review checklist, and bound JSON decision contract. Local mechanics validate gate/phase/manifest/verdict shape and route decisions separately. No real Advisor consultation or gate review has been run, so review quality, actual evidence access, model resolution, structured-output configuration, and independent behavior remain unverified.

### §4.1–§4.3 Mission, modes, and critical review

| Specification | Finding | Evidence / limitation |
|---|---|---|
| Principal-scientist/research-director posture that improves epistemic quality, not motivational agreement. | **Prompt-encoded.** | `.pi/agents/research-advisor/agent.md` assigns critique quality to the Advisor, separates ownership from the Lead, and instructs it to state uncertainty and not agree for harmony. Actual judgments have not been sampled. |
| Mode A problem solving: diagnose, offer/compare alternatives, recommend next action. | **Prompt-encoded.** | Advisor prompt has a direct Mode A procedure. |
| Mode B design review: examine assumptions, requirements, alternatives, failure modes, controls, and criteria. | **Prompt-encoded.** | Advisor prompt has a direct Mode B procedure. |
| Mode C critical manifest-bound gate review. | **Prompt and local gate record present.** | Advisor prompt defines Mode C and contract; `gates.py gate-review` checks phase/gate/manifest and records run ID, verdict, and review basis. Live gate behavior is not verified. |
| Critical review detects theoretical, source, confounding, baseline, implementation, leakage, measurement, statistical, contradiction, limitation, and question-coverage failures. | **Prompt checklist substantially matches; efficacy unverified.** | The Advisor prompt lists the corresponding failure classes and requires why/how-to-resolve explanations. No corpus of real reviews or independent review benchmark exists. |

### §4.4 Decision contract and gate behavior

| Specification | Verdict | Evidence and limitation |
|---|---|---|
| Gate, exact review target, verdict, summary, findings, alternatives, uncertainties, next actions, and missing evidence fields. | **Prompt contract plus structural validation.** | `research-advisor/agent.md` supplies the JSON shape. `gates.py validate_verdict` checks gate and manifest target, verdict enum, summary, required arrays, finding severity/fields, required findings for revise/block, and missing-evidence entries for inconclusive. It permits extra fields and does not use an explicit JSON Schema artifact; response formatting is not tested against a live model. |
| Verdict semantics and separation from routing. | **Encoded in Advisor/Lead prompts and route code.** | Prompt explains approve is not proof and the Lead routes separately. `gates.py gate-route` enforces legal route/verdict combinations, objective/cap/stagnation precedence, HOLD, and terminal status-report requirements. Local fixture tests cover malformed verdicts and route cases. |
| Fail closed on malformed, wrong gate/phase, stale target/manifest, or missing review; phase-bound protocol/readiness; bounded retries and HOLD. | **Local mechanics implemented and fixture-tested; live execution unverified.** | `check_manifest`, `validate_verdict`, `gate-review`, `latest_approval`, coverage/freshness checks, and stale-review withdrawal bind approvals to manifest bytes and phase. `test_managed.py` covers stale/malformed reviews and bounded no-verdict recovery. The ledger validates recorded run IDs but cannot prove an Advisor child actually ran or returned that output. |
| Manifest drift invalidates reliance, except explicitly covered readiness reuse. | **Manifest checks present; coverage and reuse details require later workflow-item review.** | `checks.py coverage` compares exact hashes and `gates.py` rechecks manifests before routing. This section’s basic binding requirement is present; whether the §5.3 exception is implemented is reserved for audit item 5. |
| Revise, inconclusive, and block recovery are bounded and do not silently authorize progress. | **Guarded local transitions; prompt policy remains bypassable.** | `gates.py` bounds remediation rounds, permits one inconclusive evidence-gather route/re-review before HOLD, and puts `block`/no-verdict on HOLD. Lead prompt describes human escalation. No unvalidated/unreviewed direct-host route is prevented at the Pi permission layer, consistent with blueprint’s instruction-level caveat. |
| At most two evidence-expansion rounds per gate; follow-up retains rubric, prior findings, and correct manifest version; advice cannot count as verdict. | **Prompt-encoded and partly represented in separate record types.** | Advisor prompt caps requests at two rounds; gate records use manifest/version and run IDs; `record-consultation` labels advice separately from verdict records. There is no independent live audit of follow-up packet contents or model behavior. |
| Structured output when configured, otherwise JSON; successful shape/run is not scientific proof. | **Conditional prompt support; exact provider/schema behavior unverified.** | Agent prompt says exactly JSON and explains verdict limits. No live run attests that structured output is configured/used; static smoke-roster requirements are not satisfied here. |

### §4.5 Access to primary artifacts and anti-anchoring

| Specification | Finding | Evidence / limitation |
|---|---|---|
| Advisor can read research specification, original sources, code/diffs, tests, observations, analysis scripts/statistics, and claim-evidence map; can request specific artifacts. | **Declared read capability and request behavior present; runtime scope unverified.** | Advisor declares `read/grep/find/ls`, inherits project context, and may request primary artifacts in at most two expansions. It cannot write or execute per frontmatter/prompt. No actual review packet established that all required artifacts were available/read. |
| High-risk review sequence: independent evidence-first assessment, then compare with Lead interpretation and identify disagreements. | **Not found as an explicit required procedure.** | The Advisor can access primary evidence and the Lead prompt asks for decision briefs, but the inspected prompts do not require this two-pass anti-anchoring sequence for high-risk reviews. No high-risk review was performed. |
| Correlated model errors mitigated by independent tests/human escalation. | **Instructional support; no evaluation evidence.** | Advisor and Lead prompts disclaim that approval proves truth and require tests/escalation. No system-variant or false-acceptance measurement has been run. |

**Item 4 disposition:** Review complete. The role contract and local gate validation are strong, but the blueprint is not fully demonstrated: the two-pass high-risk review procedure is absent, schema-constrained output and runtime access/model behavior are unverified, and the ledger cannot authenticate the child execution it records. No claim of successful Advisor review should be made from these fixtures.

**Next item:** §5, Research workflow design.

---

## Audit item 5 — Research workflow design (§5)

**Review completed:** 2026-11-24 (item 5; after item 4 and before item 6). **Item verdict: PARTIALLY IMPLEMENTED; lifecycle/gate mechanics are substantially present, while the research work products and empirical stages are not.** Managed state covers stages, objectives, outer cycles, inner-attempt counters, progress, blockers, gate reviews, HOLD/SUSPENDED, and guarded report/replan routes. The Lead prompt describes the dual loop. There is no live project, approved research plan, experiment execution, real gate review, or final scientific report. Some nuanced readiness, per-attempt, and artifact requirements are not validated by the state machine.

### §5.1 Dynamic dual-loop lifecycle, routing, termination, and accounting

| Requirement | Verdict | Evidence and limitation |
|---|---|---|
| Non-deterministic PLANNING → IMPLEMENTATION ⇄ EVALUATION → ANALYSIS routing; REPORTING only through approved CYCLE_GATE report route. | **Partial mechanics implemented; lifecycle remains host-driven.** | `durable.py`/`ledger.py` model stages, and `gates.py` gates protocol/readiness/inner-exit/cycle/report phases with legal routes. Lead prompt mirrors the flow. No application policy prevents direct host actions outside the ledger; no live cycle was run. |
| HOLD is resumable; SUSPENDED is terminal with preserved-evidence status report, distinct from COMPLETED. | **State distinction and checks implemented.** | `gates.py` requires a held state and report to suspend; `ledger.py` distinguishes statuses and rejects an unsubstantiated suspension; completion is reachable only via report route. Tests exercise fixture transitions, not production recovery. |
| Protocol PLAN_GATE precedes implementation; separate readiness PLAN_GATE precedes full evaluation; per-attempt checks are not approval; INNER_EXIT permits diagnosis-only but no success/report claims. | **Phase/state guard implemented; manifest semantics incomplete.** | `PHASES`, `STAGE`, `latest_approval`, and `gate-route` distinguish protocol, readiness, complete, diagnosis, cycle, and report. Diagnosis-only routing cannot claim achievement. However `check_manifest` requires a nonempty hashed artifact map and matching phase but does not require that a readiness manifest contain the specified baseline, protocol reference, and passing test evidence. |
| Inner loop stays within plan; plan-changing repair exits for diagnosis; outer replan only after CYCLE_GATE approve/replan. | **Outer replan protection implemented; per-attempt inner-loop handling partial.** | `gates.py` checks `proposed_route`, next plan and rationale, and charges only on consuming legal `approve/replan`. `begin-inner-attempt` is stage/protocol/limit guarded. It does not bind an attempt charge to an integrated code change or record no-change interruption without charge; failure-driven retry transitions remain largely a Lead instruction. |
| Achievement, unsolvable blocker, cycle-cap and early-stagnation termination conditions have specified precedence. | **Core predicates/routes implemented.** | `gates.predicates`, `ledger.termination_predicate`, and `gate-route` cover objective achievement, confirmed blockers, cap, progress verdicts, early stagnation, cap precedence, report vs replan vs HOLD/stop. Fixture regressions cover final-cycle reporting, cap repair, and block precedence. No scientific objective or real blocker has been evaluated. |
| HOLD on resource exhaustion and human authority; no spending beyond project-wide budgets. | **Prompt-only / partial counters; project-wide resource control absent.** | Lead prompt puts safety/authority/resource HOLD first. Managed state tracks cycle/inner/review/assignment limits, but not project-level token, compute, money, or external-action budgets. No provider quotas or spending limits are integrated. |
| Track cycle, per-cycle progress, inner attempt, separate review/consultation retries, and charge only at specified events; commits at gate/cycle boundaries. | **Partial.** | `durable.py`, `gates.py`, `ledger.py`, and fixture tests track cycles, progress, gate-review rows, and assignment attempts. The inner counter is an explicit manual lifecycle action, not tied to changed-work proof; no no-change interruption record exists; consultation retry limits are not separately modeled as a counter. Git checkpoint commits are not automatically required at every gate/cycle boundary (see §1/P9). |

### §5.2 Planning stage

| Specification | Finding | Evidence / limitation |
|---|---|---|
| Twelve planning activities: frame direction; prior work/literature; evidence vs open questions; research questions/hypotheses; scope/method; benchmarks/data; metrics/validity; resources/risks; roadmap. | **Mostly prompt/blueprint guidance; not performed or validated.** | Lead prompt describes lifecycle and workspace, but does not encode this complete twelve-step checklist. `research.py init` creates only a starter charter; no literature map or planning artifacts exist. There is no authorized real research direction here. |
| Six required plan artifacts (`research-charter.md`, literature review, hypotheses, methodology, evaluation plan, roadmap) and seven Advisor review questions. | **Scaffold partial; deliverables absent.** | Bootstrap creates `change-and-progress-logs/charter/research-charter.md` and directories, not the other required files. Gate review accepts a caller-supplied manifest but does not require these canonical artifact paths or run content checklist validation. No Advisor review has occurred. |
| Protocol approval before substantial implementation; protocol recorded before results where practical; exploratory changes distinguished. | **Protocol/readiness phase guard present; research protocol/preregistration not present.** | `gates.py` will not begin an inner attempt without protocol approval and phases are manifest-bound. It does not enforce preregistration timing or require exploratory labeling. No protocol artifact or evaluation result exists. |

### §5.3 Implementation stage

| Specification | Finding | Evidence / limitation |
|---|---|---|
| Decompose into bounded packages for code/data inspection, experiment components, baselines/treatments, tests, schemas/data prep, inference, reproduction commands, smoke tests. | **Assignment mechanics support packages; research implementation itself absent.** | `evidence.py` captures scope, allowed paths, inputs, commands, criteria, budgets, and status; Worker prompt scopes execution. Bootstrap creates `src/` subdirectories but no methods, baselines, tests, configs, or dataset artifacts. |
| Required versioned implementation, lockfiles/environment, dataset hashes, experiment configs, automated tests, reproducible instructions, notes. | **Not yet present in a project.** | Only repository-infrastructure tests and a reference analysis helper are checked in; there is no project-specific source or dataset. The project initializer does not produce these deliverables. |
| Separate readiness manifest with baseline, protocol ref, passed required tests; full evaluation blocked until approval. | **State transition implemented, required contents not enforced or exercised.** | `gates.py` requires current protocol approval and a valid readiness-phase manifest before full-evaluation route. Manifest checker does not semantically require the baseline/protocol/test fields. No readiness verdict or full evaluation exists. |
| Reuse readiness after later in-plan fixes only with revision/diff, passing attempt checks, and unchanged interface/contract/validity assumptions; otherwise fresh review; plan change uses diagnosis/CYCLE_GATE. | **Partially supported; substantive reuse test/record missing.** | Manifest hashing/coverage detects changed bytes and stale review; `gates.py` verifies phase and prior approval. There is no structured exact revision+diff/per-attempt check/assumption-coverage record or automated semantic assessment of unchanged validity conditions. The tracker explicitly leaves readiness reuse/drift coverage open. |
| Implementation approval is not scientific hypothesis approval. | **Explicitly encoded in prompt/contract.** | Advisor contract says approve is a gate pass, not proof; analysis helper labels output draft and not a verdict. No empirical implementation was reviewed. |

### §5.4 Evaluation stage

| Specification | Finding | Evidence / limitation |
|---|---|---|
| Freeze protocol; run baselines/treatments; save raw outputs and metadata; repeat stochastic runs; validate integrity; predefined metrics, uncertainty/effect sizes, failure/outlier investigation, ablations/robustness, deviation/exploratory labels. | **Not implemented as a research execution pipeline; only narrow analysis support exists.** | `analyze.py` consumes a paired CSV/config with hashes and seeded bootstrap, but does not run model inference, baselines/treatments, repetitions, ablations, or integrity pipelines. No raw empirical data or experiment runner exists in a project. |
| Required immutable configurations, raw results, inference metadata, scripts/figures, ablations, failure taxonomy, per-attempt deltas. | **Absent from active project; workspace directories only.** | Project initializer creates `src/experiments`, `src/configs`, and related directories but no artifacts. Managed `inner_attempt` is a counter, not a versioned result/delta record. |
| Inner-exit rubric and complete-or-diagnosis-only package before analysis. | **Gate schema supports phase and diagnosis flag; content rubric incomplete.** | `gates.py` distinguishes complete and diagnosis phases; route rules prevent diagnosis-only success. It does not require the listed evaluation artifacts or validate the Advisor’s substantive rubric; no package was submitted. |

### §5.5 Analysis stage

| Specification | Finding | Evidence / limitation |
|---|---|---|
| Compare evidence to hypotheses/alternatives; assess claims; diagnose binding plan limitation; record evidence-backed progress; propose plan deltas; preserve human-only charter changes; apply stop rules. | **Some state fields and routing guard exist; analytical artifacts and most content checks are prompt-level/absent.** | `project-state.schema.json` models objectives and progress verdicts; `gates.py` requires progress evidence references and approved replan manifest fields. It does not independently validate hypothesis comparison, limitation diagnosis, or charter-change authority beyond prompt/state action semantics. No project analysis exists. |
| Required evidence-to-hypothesis assessment, validity analysis, limitation diagnosis, progress verdict, and cycle-decision artifact. | **Partial: progress/gate records in state; required documents not guaranteed.** | Managed state stores objectives, progress and CYCLE_GATE review; `research.py init` makes a decisions directory. Gate manifest does not require a `cycle-decision.json` file or its full contents; no such artifact is present. |
| CYCLE_GATE approve required for report/replan; report route and next-cycle charging only on authorized route. | **Mechanically guarded and fixture-tested.** | `gates.py gate-route` requires approval, checks objective/cap/early-stagnation precedence, charges cycle once on `replan`, and enters REPORTING only on `report`. These tests use constructed evidence, not scientific observations or live Advisor decisions. |

### §5.6 Reporting stage

| Specification | Finding | Evidence / limitation |
|---|---|---|
| Report covers executive summary, problem/questions/literature/hypotheses/method/implementation/evaluation/results/interpretation/alternatives/limitations/conclusions/implications/reproduction/follow-up. | **High-level summary guidance only; no complete report schema/checklist.** | Lead prompt calls for an executive and technical body and preservation of limitations/negative findings. No report generator, report template, or required-section validator was found; `analyze.py draft` is explicitly not a final report. |
| Required research report, claim-evidence matrix, reproduction instructions, bibliography, final manifest. | **Workspace scaffold, not deliverables/enforced gate conditions.** | Bootstrap creates `reports/` and `manifests/`; prompt describes project layout. `REPORT_GATE` accepts a versioned manifest but code does not require these five canonical deliverables or verify claim-by-claim traceability. None is present in a real project. |
| Resolve critical findings and independently verify mandatory artifacts before final approval. | **Gate route shape present; resolution/artifact completion is not semantically enforced.** | `gates.py` validates output shape, manifest hashes and route; there is no issue-resolution linkage or mandatory report artifact inventory validator. Advisor instructions request critical review, but no report review occurred. |

**Item 5 disposition:** Review complete. Core gate/cycle control is one of the strongest implemented areas and fixture regressions cover key routes. The blueprint’s substantive planning, implementation, empirical evaluation, analysis, and reporting artifacts are **not complete**; current code is lifecycle/assignment scaffolding plus a narrow paired-analysis helper. Readiness manifest contents/reuse, integrated-change-based inner-attempt charging, research artifact completeness, and final-report claims checks remain gaps.

**Next item:** §6, Advisor consultation and context engineering.

---

## Audit item 6 — Advisor consultation and context engineering (§6)

**Review completed:** 2026-11-24 (item 6; after item 5 and before item 7). **Item verdict: PARTIALLY ENCODED; most context-engineering mechanics are not implemented.** Prompts require focused, decision-oriented briefs, primary evidence, fresh context, and bounded gate evidence expansion. The project state can record that a consultation happened. There is no structured consultation-package builder/validator, quality checklist, token/cost budget system, per-issue attempt budget, consultation cache, or adoption/empirical-outcome tracking. No real consultation was made in this audit.

| Blueprint subsection | Specification and finding | Evidence / limitation |
|---|---|---|
| **§6.1 Objective** | The objective is better research decisions per consultation cost without discarding necessary evidence. **Not operationalized or measured.** | Lead prompt asks decision-oriented briefs and cites; `gates.py record-consultation` records outcome references. No optimization metric, cost attribution, or study of consultation benefit per unit cost is present. |
| **§6.2 Structured package** | Package should include consultation identity/type, stage/task, precise decision and impact, verified facts, current approach/rationale, uncertainty/alternatives/failure modes, evidence, constraints, and requested output. **No matching schema/template or builder found.** | `.pi/agents/research-lead/agent.md` tells Lead to send focused decision briefs and cited artifacts, but project-state `consultations` stores only a limited observation (agent, run ID, status, evidence reference). The Advisor prompt can request evidence but does not define the whole packet schema. Fresh context is declared in its frontmatter; actual launch context is unverified. |
| **§6.3 Prioritization** | Order information by decision, impact, facts, approach, uncertainty, evidence, constraints, requested output; exclude full histories, unrelated literature, logs, large files, resolved decisions, ordinary narration. **Not encoded as a complete rule/checklist.** | The Lead’s brief guidance supports concise context and primary references, but the exact prioritization/exclusion rules and content validation are absent. No real packet was inspected. |
| **§6.4 Progressive disclosure** | Two-level brief then exact evidence expansion; reasonable initial 1,000–2,500 input token engineering target; never compress below sufficiency; expansion bounded. **Partial.** | Advisor prompt requests specific artifacts and caps gate expansions at two; Lead prompt requests focused briefs. No packet-size/input-token measurement or explicit two-level task schema exists. The evidence-expansion prompt is not backed by an end-to-end packet trail in this checkout. |
| **§6.5 Quality checks** | Verify specificity, decision, assumptions, facts-vs-hypotheses, sources, alternatives, actionability, and missing-information risk before every call. **Not encoded as a pre-dispatch checklist or verified behavior.** | No consultation validator/helper/test was found. General judgment instructions are not equivalent to the explicit checklist. |
| **§6.6 Example** | Poor/effective consultation examples illustrate the quality distinction. **Illustrative, not an independent executable requirement.** | The blueprint itself contains the examples; no corresponding code is expected. No sample consultation corpus demonstrates adoption. |
| **§6.7 Overload controls** | Separate mandatory/exploratory budgets, per-call token/inference limits, per-issue attempt cap, reuse/cache for equivalent evidence/questions, invalidation on changes, and track adopted/rejected/validated advice. **Mostly not implemented.** | Gate review rounds are bounded; manifests and the execution ledger can invalidate evidence consumers after supersession. `consultations` does not track tokens/cost, same-issue attempts, cache keys, advice adoption, or empirical validation. External model budgets are an open tracker item. |
| **§6.8 Avoid bottleneck** | Mandatory/high/normal/low consultation priority; never skip gates for budget; exhausted budget HOLDs or narrows scope. **Partial prompt-level behavior.** | Lead prompt marks gate calls mandatory and resource/authority HOLD precedence; missing priority classes and separate consultation budgets mean normal/high/low routing and cost decisions are not implemented. |

**Item 6 disposition:** Review complete. The basic goal of concise, evidence-oriented Advisor requests is present in prompts, and gate evidence requests are bounded. The blueprint’s consultation artifact shape, pre-call quality gate, resource controls, reuse/cache semantics, and value tracking are **not fully implemented**. Any claim that context engineering has reduced cost or improved consultation quality lacks empirical evidence.

**Next item:** §7, Research artifacts, knowledge, and memory.

---

## Audit item 7 — Research artifacts, knowledge, and memory (§7)

**Review completed:** 2026-11-24 (item 7; after item 6 and before item 8). **Item verdict: PARTIALLY IMPLEMENTED; project scaffold and local evidence manifests exist, but a populated durable research record and claim-level traceability do not.** The bootstrap creates a basic per-project workspace/state/Beads binding; manifests and hashes bind evidence for reviews/assignments; OKF reader/writer agents and validators exist. No project workspace or empirical artifacts were present. Several canonical hub artifacts and the manifest/report/claim matrix are not created or enforced, and external content-addressed storage is not implemented.

### §7.1 Artifacts as source of truth

| Specification | Finding | Evidence / limitation |
|---|---|---|
| Project identity plus durable tasks, sources, experiment runs, decisions, reviews, and final deliverables; chat histories are not primary research records. | **Architecture and state scaffolding present; actual research record absent.** | `research.py init` assigns project ID, creates managed `project-state.json`, separate project-bound Beads SQLite, starter charter, and artifact directories. The ledger stores gate/execution records; `todos.md`/README explicitly state Pi run artifacts are not the durable source of truth. No `research-projects/` directory or completed research corpus is present. |
| Versioned durable records are available for resume/audit. | **Partial local mechanics.** | Ledger revisioning/operation receipts, manifests, artifact hashes, and Git checkpoint checks exist. The design requirement for commit checkpoints is not enforced at every gate/cycle (item 1/P9); no live project resume was tested. |

### §7.2 Project structure and governance hub

| Specification | Verdict | Evidence / limitation |
|---|---|---|
| Separate global agent definitions/tools from per-project evidence. | **Implemented structurally.** | Fixed roles live in `.pi/agents`; Beads extension and settings are under `.pi`; project bootstrap targets `research-projects/<id>/`. The root and `.pi` are separate Git checkouts. |
| Canonical project layout: charter/scope; planning artifacts; review folders; decision log/cycle decision; literature sources/review/notes; `src/{methods,tests,evals,experiments,configs}`; report; manifest; managed project state. | **Bootstrap scaffold is partial; required files/data are absent.** | `research.py initialization` creates charter directory/file, planning/reviews/decisions directories, literature directory, `src` subdirectories, reports/manifests/runtime, and project state. It does not create `scope-and-constraints.md`, hypotheses/methodology/evaluation-plan/roadmap, review subfolders, decision log/cycle-decision, literature source/review/evidence files, report, or `artifact-manifest.json`. No active project exists to contain the artifacts. |
| Governance hub `change-and-progress-logs` is authoritative/indexed; director brief and every change/review/decision/cycle artifact is available for resumption and REPORT_GATE. | **Prompt and directory scaffold present; indexing/record publication incomplete.** | Lead prompt defines the hub, index and writer/reader division; bootstrap creates a minimal OKF `index.md` with the starter charter link. Gate reviews/counters are stored in managed project state, but no code checks that every gate/cycle decision is filed/indexed in the hub. `director-brief.md` and complete hub contents are not generated. |
| Hub uses OKF v0.2 with local canonical spec copies and validator; writer maintains records while Lead owns state/counters/checkpoints; reader retrieves. | **Definitions, specs, validators, and partial precheck implemented.** | Reader/writer prompts and local validators exist; the reader/writer `.pi/agents/*/spec` trees were compared and are identical. `checks.py okf_precheck` invokes writer/reader validators and checks local links/created concepts. Actual project bundle publication/retrieval has not been exercised. The writer workflow’s staging and semantic safeguards are prompt procedure, not OS/file transaction enforcement. |
| Machine-owned JSON (`cycle-decision`, manifest, project state) is indexed but not rewritten as OKF concepts; execution code stays under `src/`; large outputs can be content-addressed outside Git. | **Partial / not implemented.** | Project-state and manifests are structurally separate from concept records; Worker prompt says project state is Lead-owned and execution artifacts are produced directly. However no file path/content check enforces hub indexing of machine records or `src/`-only research code. `checks.manifest` hashes files rooted within the project; no external content-addressed artifact-store adapter/location resolver was found. |
| Pi child/session history is not permanent research truth; findings are copied/referenced into durable project artifacts. | **Prompt/runbook-encoded, operationally unverified.** | README and Lead prompt require durable results and exact run references; ledger records references. No child run was performed to test reconciliation into a real project. |

### §7.3 Research knowledge organization

| Knowledge category | Finding |
|---|---|
| Research literature | `literature/` scaffold and `okf-reader` can retrieve a supplied bundle; no source catalog/literature review or external paper retrieval was performed. **Partial.** |
| Project knowledge (goals, hypotheses, decisions, constraints) | Starter charter and managed objectives/decisions exist; hypotheses/scope/decision artifacts are not initialized or populated. **Partial.** |
| Experimental evidence (methods/configs/outputs/metrics) | `src/` and experiment directories are created; `analyze.py` supports one paired-CSV format, but no execution evidence exists. **Scaffold only.** |
| Operational knowledge (tools/procedures/failures/practices) | README, ledger, validator and role docs provide operational guidance; no research-project incident/failure corpus or retrieval test exists. **Partial.** |
| Retrieve minimum knowledge for active task; avoid premature complex knowledge graph. | **Prompt/architecture fit.** | OKF reader contract requests minimum sufficient attributable evidence and gaps; no knowledge graph was introduced. Retrieval quality in live use remains unverified. |

### §7.4 Claim-to-evidence traceability

| Specification | Finding | Evidence / limitation |
|---|---|---|
| Each important research claim has an ID, statement, status, evidence references, and limitations; Advisor agreement cannot turn a hypothesis into verified fact. | **Not implemented as a claim registry/matrix.** | `project-state` objectives contain evidence refs and assignment/gate manifests hash artifacts; `analyze.py` output records input/config hashes and limitations. No `claim_id` model, claim status/evidence mapping validator, or `claim-evidence-matrix.md` is present in the operations toolset. Lead prompt says an Advisor pass is not truth, but no claim-level gate enforces it. |

**Item 7 disposition:** Review complete. The durable workspace concept is represented in bootstrap, prompt, state, and validation components, but the actual knowledge base is an empty scaffold and lacks multiple canonical artifacts. Claim-level traceability and external immutable artifact storage are not implemented; no final research evidence or reporting corpus is available.

**Next item:** §8, Host orchestration, state, and execution contracts.

---

## Audit item 8 — Host orchestration, state, and execution contracts (§8)

**Review completed:** 2026-11-24 (item 8; after item 7 and before item 9). **Item verdict: SUBSTANTIAL LOCAL MECHANICS, BUT ONLY PARTIAL SPECIFICATION CONFORMANCE.** The managed ledger, phase-bound gates, explicit Beads adapter, expected revisions/receipts, assignment evidence lifecycle, hashes, integration checkpoints, supersession and local status views are substantive implementations with passing fixture/native-DB tests. They do not observe live child behavior, enforce OS confinement, transactionally coordinate the stores, or implement project-wide spend/sandbox controls. The formal snapshot schema and some lifecycle charge details also remain incomplete.

### §8 intro and §8.1 Project/task records

| Requirement | Verdict | Evidence and limitation |
|---|---|---|
| Research-domain state is durable and separate from Pi execution/run state; use project artifacts, not chat history, as source of truth. | **Implemented as architecture and record tooling.** | `durable.py`, `ledger.py`, `evidence.py`, `project-state.schema.json`, and `research.py` manage a project-bound state, records, manifests, and run references; README distinguishes Pi runtime from durable evidence. No live project resume was exercised. |
| Record project ID, research direction/objectives/constraints/resource budget; stage/cycles/plan/protocol/tasks/dependencies/criteria/attempts; sources/hypotheses/decisions/evidence/hashes; consultations/reviews/run IDs; task links and human decisions. | **Partial.** | Managed state contains identity/charter ref, lifecycle, outer-cycle budget, objectives, progress, blockers, consultations, decisions, gate reviews, and assignment/evidence records. The research direction and knowledge artifacts are expected in charter/hub; structured constraints, hypotheses, approved protocol, and per-budget-class costs are not represented in the managed schema. Beads owns backlog/dependency fields without duplication. |
| Manifest-bound approval distinguishes submitted from approved artifacts; task completion requires criteria and verification; child `complete` is not acceptance/scientific validity. | **Local mechanics present.** | Gate records bind gate/phase/target and verify artifact hashes; assignment result, Lead decision, availability/integration, and Beads closure are distinct. Tests cover stale manifests, valid/invalid acceptance, and real Git artifact checkpoints. The ledger cannot prove a claimed external check ran or that the child result is true. |

### §8.2–§8.3 Consultation/review and assignment references

| Requirement | Finding | Evidence / limitation |
|---|---|---|
| Every meaningful task gets structured readiness; factual/technical uncertainty is investigated, conceptual/methodological uncertainty is consulted, and authority gaps pause for human input. | **Important gap.** | See item 3: no general readiness classifier/dimensions or durable READY/INVESTIGATE/CONSULT/BLOCKED record. Managed `mark-ready` applies to an issued Worker/pool brief only. |
| Advisor invoked directly with fresh context, focused brief, and primary artifacts; result inspected and recorded; invalid/unavailable result HOLDs dependent gate; no substitute. | **Prompt/validator scaffolding present; actual calls unverified.** | Advisor frontmatter/prompt declares fresh/read-only behavior; `gates.py` validates records and no-verdict HOLDs; `record-consultation` is separate from gate verdicts. Runtime execution/response evidence is absent. |
| Assignment and acceptance follow §§8.9.1/8.9.4, and Advisor/OKF results retain separate authority. | **Mostly implemented locally.** | Assignment lifecycle in `evidence.py`, typed Beads tools, and distinct Advisor/OKF contracts are present. No end-to-end live assignment was run. Detailed clause audit appears under §8.9 below. |

### §8.4 Loop-aware progression, authoritative route table, resumption

| Route/state rule | Finding | Evidence / limitation |
|---|---|---|
| Separate protocol/readiness approvals; complete vs diagnosis-only exit; `REPORTING` only via approved CYCLE_GATE; final completion only via REPORT_GATE. | **Implemented in guarded ledger transitions and fixture-tested.** | `gates.py` phase/stage map and route checks implement these distinctions; `test_managed.py` exercises the full simulated lifecycle, including final-cycle achievement and stale reviews. This is not non-bypassable against direct host actions. |
| Protocol/readiness revise, bounded inconclusive evidence, block/no-verdict HOLD, manifest drift, revise limits. | **Mostly implemented in local state machinery.** | Gate records and route counters are separate by cycle/phase; no-verdict retries are bounded, block sets HOLD, stale records can be withdrawn, and approved routes require fresh hashes. Retries are records in the managed ledger; no actual Advisor execution or evidence expansion was performed. |
| CYCLE_GATE precedence: achievement before cap; only approved justified replan charges a cycle; cap/stagnation prohibits new cycles; in-plan remediation remains possible; block/inconclusive/no-verdict retain their route. | **Implemented for ledger-mediated routes; fixture-tested.** | `gates.predicates`, `gate-route`, and tests cover the listed route precedence and replan authorization. A gate candidate/status view does not itself run or constrain the host. |
| HOLD/SUSPENDED/report distinction, status report, human authorization for unresolved blockers/resource stops. | **State checks present, report substance/human exchange unverified.** | `open-hold`, `resolve-hold`, and `suspend-held` require stated conditions and a status-report string; the Lead prompt assigns escalation to the human. No actual report content, resource hold, or director decision was tested. |
| Cycle 1 is charged at initial planning; later cycles charged once on approved replan; failed PLAN_GATE does not refund; revisions do not alter plan/counters. | **Later-cycle charging guarded; initial charge timing differs.** | `durable.new_state` sets `outer_cycle=1` and `budgets.outer_cycles.used=1` at project initialization while lifecycle stage is `CREATED`, before `start-planning`. Blueprint says charge cycle 1 at the start of initial planning. `gates.route=replan` increments once with operation receipts and resets `inner_attempt`; failed PLAN_GATE does not refund. |
| Charge inner attempts when implementation changes are integrated; log no-change interruption without charging; track review and consultation retries separately. | **Partial; inner charge is not tied to change evidence.** | `begin-inner-attempt` increments the counter in `gates.py`; it does not require an integrated revision/commit or record a no-change interruption. Gate-review records provide review history; consultation records contain outcomes but not a complete separate retry budget. |
| Resume from state and artifacts, verify previous run/review evidence, reconcile disagreement, never infer approval. | **Instructions and read views present; live recovery unverified.** | Lead prompt requires `status` on startup/resume/before gates; `ledger status/next/progress/termination-check` include revision/timestamp and flags; README requires reconciliation. No host interruption/persistent child run was tested against a live Pi run. |

### §8.5 Bounded autonomy and budgets

| Resource class | Finding | Evidence / limitation |
|---|---|---|
| Outer cycles 3–5, inner attempts, gate revise rounds, evidence/review retries. | **Partially implemented.** | Outer max is validated in range; inner limit, gate remediation rounds, and evidence attempts are modeled. Initial charge timing and inner charge-evidence issues are noted above; consultation/evidence expansion attempts are not all represented as separate counters. |
| Worker/pool attempts, soft deadline, hard cutoff, usage limits. | **Assignment records present; runtime control absent.** | Briefs require attempt/soft/hard limits; cutoff, termination, no-result, and effect reconciliation are distinct records. These operations record observations supplied by the Lead; there is no host process supervisor that proves a child stopped or enforces a hard kill here. |
| Experiment run/wall-clock, model token/cost, API spend, CPU/memory/storage/network budgets and quotas. | **Not implemented.** | Managed `budgets` schema contains outer cycles only; assignment briefs add local limits. No usage, provider quota, external expenditure, or sandbox resource integration exists. Tracker and README explicitly leave this open. |
| Budget exhaustion stops governed work; project-wide exhaustion HOLDs for director decision; no positive conclusion forced. | **Prompt-encoded; cannot be mechanically verified.** | Lead prompt gives resource HOLD precedence and human stop authority. No observed spending data, quota, or resource HOLD exists. |

### §8.6 Director communication contract

| Specification | Finding | Evidence / limitation |
|---|---|---|
| Dated standing brief refreshed on cycles/report/decisions/status/budget changes, contains status/changes/decision/next checkpoint and sourced spend. | **Prompt-encoded, no automation or project artifact.** | Lead prompt instructs the Lead to use `okf-writer` for `director-brief.md`; bootstrap does not create this file and there is no updater/scheduler. Spend source/coverage cannot be reported without external usage data. |
| DECISION-REQUIRED vs FYI, real authority parks dependent work; clear/ambiguous replies recorded and read back; stop order honored. | **Prompt and state tags present; interaction behavior unverified.** | Lead prompt contains tags and response procedure; project schema has decision tags/status. No actual director message/decision/resume cycle was exercised. |
| Scope failures by dependency; notify promptly when mandatory calls fail; only designated result satisfies required gate; no project-wide HOLD for optional failure. | **Partially supported.** | Beads dependencies, optional-drop checks, assignment status, and gate-specific HOLD exist; Lead prompt specifies dependency scope and notification. Live failure-isolation and director notifications were not tested. |
| Final report has executive and technical body; summary alone preserves limitation/negative/action boundary. | **Prompt-level requirement; no report validation.** | Lead/Advisor prompts repeat the audience requirement, but no summary-specific rubric or report content is present. See §5.6. |

### §8.7 Knowledge-service delegation

| Specification | Finding | Evidence / limitation |
|---|---|---|
| Reader retrieves scoped evidence and gaps; writer performs bounded record/index/log mechanics; Lead owns content/judgment and spot-checks results. | **Role contracts present.** | `okf-reader`/`okf-writer` prompts and local v0.2 specs define the split; `checks.py okf_precheck` invokes validators and index/disk reconciliation. No live service result was tested. |
| Validate writer bundle/result and reader result; stale/malformed required result or failed validator HOLDs dependent gate; Advisor still checks truth. | **Validators and check helper exist; gate coupling is manual/prompt-level.** | `checks.py okf_precheck` runs writer bundle/result and optional reader envelope checks. `gates.py gate-review` does not itself require/verify an OKF precheck receipt or required-service result; no service receipt was consumed at a gate. |
| Serialize hub mutations and reconcile partial writes; keep direct director path and service-outage rules. | **Prompt/runbook only; no hub lock/lease.** | Writer prompt requires one in-flight mutation, staged validation and recovery; project-state writes use `durable.lock`, but that lock does not serialize arbitrary hub files/writer runs. The single-Lead-session rule is documented, not a lease. |

### §8.8 State-driven awareness

| Specification | Verdict | Evidence and limitation |
|---|---|---|
| Formal state snapshot, stage/cycle/gates/objectives/blockers/budgets/consultations/assignments/decisions and evidence links. | **Substantial managed state, incomplete against full schema.** | `project-state.schema.json`, `durable.py`, and `ledger.py` model most operational fields, but `todos.md` leaves formal schema validation open; budgets do not cover every class and several research-domain fields remain artifact references rather than structured fields. Manual invariant validation exists but is not a full JSON Schema validator across all snapshots. |
| Derived status/next/progress/termination views with generated timestamp/source revision; candidate routes are not authorization. | **Implemented.** | `ledger.py` emits `meta.generated_at`, managed revision, gate flags, execution view, candidates, cycle/objective rollups, and termination predicates; Lead prompt says the Lead selects legal routes. |
| Invariants on reads: fresh valid gate, HOLD dependencies, evidence-backed `met`, no silent repair; status on startup/resume/before gates. | **Partial.** | `check_invariants`, `gates.flags`, `evidence.check_consumer`, and read commands validate structural state, stale manifests, pins, and objective evidence; Lead prompt prescribes consumption points. Complete schema/invariant coverage remains open and no active project/resume was tested. |

### §8.9 Assignment ledger and delegation lifecycle

| Specification | Verdict | Evidence and limitation |
|---|---|---|
| **Resource model / task separation:** one explicit pinned Beads v0.49.6 SQLite database per project; no fallback; Beads owns backlog/dependencies while ledger owns execution/evidence. | **Implemented and native-DB tested.** | `research.py` binds exact `.beads/beads.db`; adapter validates version/backend/path and uses explicit arguments. `adapter.ts` exposes typed semantic tools only; no generic executor/delete. `adapter.test.ts` passes against real disposable SQLite. |
| **Exact IDs and lifecycle records:** task→assignment/revision→attempt/run→result→Lead decision→availability/use; no duplicated backlog graph. | **Implemented in data model.** | `evidence.py` stores separate record tables, validates ID relationships and source pins, retrieves historical revisions, and checks linked task IDs. `ledger.py` uses atomic locked writes, expected revisions, unique operation receipts, and replay refusal. Fixture tests exercise stale revisions/op replay and concurrency. |
| **Brief/READY:** one assignee; scope, deliverable, criteria, exclusions, pinned versions, read/write paths, commands/tools/external actions, deadlines; fresh readiness before reserve. | **Schema/mechanics implemented, broader §3 task readiness missing.** | `evidence.issue` validates the assignment fields and mode/path constraints; `mark-ready` pins a basis and reserve requires active READY revision and profile reference. It does not implement the all-meaningful-task assessment or guarantee that the task was correctly classified against role scopes. |
| **Beads operations:** exact get, combined lexical/structured query, ready/blocked/dependencies, update, guarded close/reopen, no delete/generic passthrough. | **Implemented; real disposable DB tests pass.** | `adapter.ts` enforces explicit status/filter scopes and IDs, shell-free `execFile`, DB/version checks, task prefix, queueing, guarded closure via ledger evidence, optional-drop prerequisite protection, and reopen-by-ID. Test coverage includes closed exact retrieval and no missing-database fallback. |
| **Dispatch intent/replay/recovery:** persist unique attempt before launch; only fresh uninterrupted reservation authorizes one call; unknown launches block retry; reliable run correlation required; no exactly-once claims. | **Ledger mechanics implemented; Pi process correlation unverified.** | `evidence.transition` records `dispatch_pending`, exposes a one-call fresh reservation receipt, makes replay non-launchable, and has `launch_unknown`/`prove-non-dispatch` states. The extension does not launch a child or observe Pi runtime receipts; interrupt cases in tests are simulated. |
| **Effects/termination:** single writer by default; no retry until prior run/effects settled; hard cutoff distinct from actual process exit; reconcile workspace/external effects. | **Record guards implemented; actual containment/termination is unverified.** | `reserve` checks base Git HEAD and overlapping unresolved workspaces; separate cutoff, observed termination, no-result, and effects disposition records exist. These are supplied observations; no supervisor kill, workspace quarantine, external-effect recorder, or live interruption probe is present. |
| **Result/acceptance/integration:** exact echoed IDs; source pin checking; structured status/gaps/checks; reject late/partial/failed results; Lead independently accepts; workspace delivery must be hash-verified in Git checkpoint before availability/use/Beads close. | **Strong local implementation and tests.** | `evidence.py` checks result IDs/source pins/timeliness/commands, acceptance status and exit codes, exact artifact hashes, Git ancestry/committed bytes, evidence use, transitive invalidation, and close eligibility. `test_managed.py` uses a real Git checkpoint; native Beads tests verify interrupted-close recovery. Actual child-delivered output is not tested. |
| **Supersession/revalidation:** preserve history; invalidate downstream uses/gates; no silent substitution. | **Implemented locally; runtime use unverified.** | `evidence.invalid_consumers`, gate flags, use pins, and supersession checks preserve old records and identify transitive consumers; fixture test covers a downstream gate. No live research artifact was superseded. |
| **Profile/tool enforcement and permissions:** verify actual runtime profile/capabilities at each launch; assignment scope and role authority cannot be bypassed directly or through `codemode`. | **Not fully implemented; prompt/record-only.** | `checks.pool_profile` compares supplied approval/observation, and assignment records capture grants; `reserve` accepts any nonempty `profile_ref`. Neither resolves the profile nor connects the comparison receipt to the reservation. README explicitly says no OS file/command/network confinement. Direct and `codemode` probes are open. |
| **Transactions and concurrency:** do not imply atomicity across Beads/Pi/Git/ledger; serialize state and reconcile exact IDs. | **Partially implemented and correctly caveated.** | `durable.py` locks/atomically replaces project state; adapter serializes calls within its process only and disclaims out-of-band writers. README says cross-store operations are not transactional and prescribes reconciliation. No distributed lease or live cross-store interruption test exists. |

**Item 8 disposition:** Review complete. The assignment/ledger and phase-route mechanics substantially implement the written contracts and have the strongest local tests in this repository. They remain a trusted-Lead evidence ledger rather than a runtime sandbox or Pi process supervisor. Key gaps are formal schema breadth, cycle-1/inner-attempt charging semantics, all-task readiness, project-wide budgets, OKF/gate coupling, hub serialization, exact profile-to-reservation binding, live dispatch/termination/confinement, and direct-host bypass prevention.

**Next item:** §9, Scientific rigor and evaluation policy.

---

## Audit item 9 — Scientific rigor and evaluation policy (§9)

**Review completed:** 2026-11-24 (item 9; after item 8 and before item 10). **Item verdict: PARTIALLY ENCODED; NOT IMPLEMENTED AS A RESEARCH STUDY.** A deterministic paired-analysis helper validates a narrow input shape, hashes inputs/config, calculates a seeded bootstrap interval, and emits a clearly labeled draft with limitations. Prompts state some epistemic guardrails. No research protocol, held-out dataset, model runs, independent judgment validation, or claim-evidence matrix is present; no real scientific result can be inferred.

| Blueprint subsection | Finding | Evidence / limitation |
|---|---|---|
| **§9 overall validity vs operational completion** | **Explicitly represented in contracts; no real study.** | Advisor/Lead prompts state gate approval or child completion is not scientific proof; `analyze.py` labels its output a draft and bounds interpretation. No scientific result has been produced. |
| **§9.1 Research design requirements** | **Not represented as a complete protocol schema/checklist.** | The blueprint requires question, hypothesis, competing explanations, unit, variables, controls, baselines, validity and falsification criteria. `research.py init` stores a question/objectives in a starter charter; `analyze.py` requires metric, baseline, candidate, limitation, seed, sample count and input hashes. It does not require the rest of the design fields or a protocol approval artifact with those fields. |
| **§9.2 Preferred verifier hierarchy** | **Partially reflected in local test/analysis infrastructure.** | Python/TypeScript tests, real disposable Beads/Git checks, and the paired numerical helper are deterministic evidence for their tested behaviors. No configured gold dataset, external reference implementation suite, expert rubric, or LLM-judge validation pipeline exists. No policy/tool check ensures an LLM judge is not the sole verifier for deterministically checkable claims. |
| **§9.3 LLM experiment controls** | **Mostly not implemented.** | `analyze.py` consumes paired scores and records config/raw SHA-256, seed, Python version, metric/variants, and a limitation. No experiment runner records exact model/config/prompt/harness versions, data split, repeated inference, compute equality, cost, latency, failures/exclusions, or grader validation. These items are open in the tracker’s scientific/deployment work. |
| **§9.4 Observation vs interpretation vs causal claim** | **Prompt-level and narrow draft support.** | Advisor prompt separates established claims, explanations, and speculation; Lead prompt asks for limitations/uncertainty; analyzer labels a measured `Observation` and `Scope limitation`. There is no typed claim registry or rule that distinguishes observation/interpretation/causal status across a final report; no causal analysis was performed. |
| **§9.5 Cycle comparability and exploratory labeling** | **Prompt-encoded; only partial structural support.** | Lead prompt states objectives/success criteria freeze without human authorization, non-comparable results must be marked, development separated from confirmation, and post-observation changes are exploratory unless confirmed. Managed objectives retain their text while status/evidence update; cycle/plan versions and manifest hashes exist. There is no field for development-vs-confirmation evidence or comparability label, and no code detects metric/hypothesis changes or requires confirmatory evidence for a report route. |

**Item 9 disposition:** Review complete. The reference analysis helper is scientifically cautious within a narrow paired-score use case, but does not implement the blueprint’s study design/evaluation system. Scientific performance, validity, and system-variant claims remain unverified. Per the Director’s clarified sequencing, formal empirical evaluation is **deliberately deferred** until actual runtime development produces a useful evidence base; it remains necessary before making effectiveness claims, but is not a prerequisite for safe iterative debugging.

**Next item:** §10, Pi implementation architecture.

---

## Audit item 10 — Pi implementation architecture (§10)

**Review completed:** 2026-11-24 (item 10; after item 9 and before item 11). **Item verdict: STATIC ARCHITECTURE AND MECHANICAL TOOLS ARE SUBSTANTIALLY PRESENT; DEPLOYMENT EXIT IS NOT MET.** Main-session Lead startup, role definitions, pinned-version checks, typed task tools, manifest/ledger validators, and a smoke-attestation validator are implemented. Exact deployed role resolution, effective provider/model and overrides, structured-output behavior, nested call edges, confinement, and live smoke runs remain unverified. No OS sandbox or production capability boundary is provided by prompt/frontmatter alone.

### §10.1–§10.5 Platform, definitions, dispatch, and initial stack

| Subsection / requirement | Finding | Evidence / limitation |
|---|---|---|
| **§10.1 Target platform:** Main Pi session is Lead host; existing `pi-subagents` starts children; no separate workflow engine/Lead child. | **Implemented as intended architecture.** | `research.py lead` appends the Lead prompt and invokes Pi host; no lifecycle workflow engine/Research Lead child definition is present. Runtime dispatch remains dependent on operator setup. |
| **§10.2 Agent definitions:** Lead prompt is host-only and excluded from catalog; seven fixed children are canonical; pinned Pi/Subagents versions; correct frontmatter, context, tools, models and allowed delegation edges are verified at runtime. | **Files/static checks present; required live verification absent.** | `.pi/settings.json` excludes `agents/research-lead`; `research.py preflight` pins Pi 1.6.0, `pi-subagents` 0.89.2, Beads 0.49.6, fingerprints seven definitions and checks their canonical names. `verify_smoke` validates supplied seven-role run/model/override/tool/fresh-context evidence and probe hashes, but does not run children or independently authenticate operator evidence. No attestation is present. Exact frontmatter semantics, fresh-context contents, effective tools/indirect calls, model overrides, schema-constrained output, and Worker→architect discovery remain unverified. |
| **§10.2 Pool qualification:** Compare each chosen pool candidate’s actual definition/model/override/effective tools/indirect tools/model endpoints to explicit operator approval before every launch/retry; refuse ambiguity/drift/delegation. | **Comparison helper implemented; runtime resolution and refusal path unverified.** | `checks.py check-pool-profile` compares complete supplied approval/observation records and detects selected prohibited indirect tools; it explicitly does not discover/runtime-enforce. No operator approval/profile/run exists. |
| **§10.3 Advisor dispatch:** Lead directly invokes fresh `research-advisor` with focused task/rubric/artifacts, consumes result/status, and records findings; no dispatch acceptance is treated as review completion. | **Prompt and ledger design present; no observed call.** | Lead/Advisor prompt and gate state support the requirement. No configured `subagent` run or response schema test exists in this session/deployment. |
| **§10.4 Worker/pool dispatch:** Host uses §§8.9/10.2; no required lifecycle workflow script. | **Assignment implementation present; operations unverified.** | `evidence.py`, `ledger.py`, and Beads adapter cover the record lifecycle; a dispatch script is deliberately absent. No live Worker or pool attempt was executed. |
| **§10.5 Suggested stack:** Pi/Subagents, role files, project Git, experiment/data analysis, literature sources, validators, observability. | **Partial.** | Pi/Beads pins, Python stdlib research-ops, TypeScript extension, Git evidence checks, reference paired analysis, OKF validators, and durable ledger are present. Academic search APIs/tools, model experiment runner, external immutable artifact store, full observability/usage accounting, and isolated execution are not implemented. |

### §10.6 Tool permissions and security

| Role/security clause | Verdict | Evidence / limitation |
|---|---|---|
| Lead host uses its configured tools, calls fixed roles/approved pool, and owns artifact changes/acceptance. | **Prompt/launcher boundary present; deployment-specific host permissions unverified.** | Lead prompt owns role routing and acceptance; default launcher is planning-only and delegation requires attestation. The host’s actual production tool configuration is not inspected here. |
| Advisor is read-only, no write/edit/general shell or nested delegation. | **Declared allowlist present; effective and indirect access unverified.** | Advisor frontmatter allows `read, grep, find, ls`; prompt prohibits execution/delegation. Runtime roster/callable tool inspection for the Advisor was not captured. |
| Worker has bounded write/command tools, skills, exact path scope, depth-2 skill-directed Worker→architect delegation only, no Advisor/Lead/governance authority. | **Prompt/frontmatter present; confinement and edge enforcement missing/unverified.** | Worker declares `edit/write/bash/subagent`, depth 2, skills, and prohibitions. No direct/`codemode` denied-path, command, network, or Worker→three-architect probes were performed; assignment grants do not create an OS sandbox. |
| Pool access is intersection of approved profile and assignment; `codemode` reaches only approved tools/endpoints; irreversible/external actions require host-level controls. | **Assignment metadata/comparator and documentation only.** | Ledger brief captures path/command/tool/external-action grants; comparator lists indirect tools/endpoints. Neither constrains host tool execution at the OS boundary. No actual sandbox, quotas, external-action approval extension, or pool test is present. |
| Sandbox, filesystem/network boundaries, secret controls, resource quotas, prompt-injection defenses; untrusted retrieved content is data, not authority. | **Major unresolved security requirement.** | Beads adapter safely binds its own narrow tools and OKF prompts treat bundle contents as untrusted. The Lead, Advisor, and Worker prompts do not encode a complete retrieved-content/prompt-injection defense, and no host/tool-layer isolation, secret boundary, network policy, or resource sandbox was verified. The runbook explicitly says Pi tool allowlists are not OS isolation. |

### §10.7 Deterministic orchestration toolset

| Tool/contract | Finding | Evidence / limitation |
|---|---|---|
| `validate-verdict`, `verdict-still-covers`, `okf-gate-precheck`. | **Implemented as deterministic CLI helpers.** | `tools/research-ops/checks.py` implements all three, with manifest hash and validator/link checks. OKF precheck is a Lead-run command; gate transitions do not automatically require/verify its result record. |
| `ledger` status/next/progress/termination/get/apply; exact state events/receipts. | **Implemented; fixture tested.** | `ledger.py`, `durable.py`, `gates.py`, and `evidence.py` expose managed operations, views, expected revisions, atomic locked writes, operation IDs/receipts, and stale/consumer flags. `project-state.schema.json` exists, but full formal-schema coverage remains an open tracker item. |
| Typed Beads task tools. | **Implemented; integration-tested on disposable SQLite.** | `.pi/extensions/beads-tools/{adapter.ts,index.ts}` registers nine semantic host-only model tools and forbids generic CLI/delete. Native test suite passed (2 integration tests). Child/OS access beyond this extension remains a deployment probe. |
| `preflight`, `freshness-flags`, `smoke-roster`, record tool versions/results and fail closed when required checks fail. | **Partial; precise contract mismatch and operational gap.** | `preflight` verifies installed pins/bindings/fingerprints and static seven-role definitions; it does **not** itself output effective model/override per role as the §10.7 table says. `smoke-roster` validates operator-supplied observations and explicitly cannot certify truth. Freshness checker exists. Gate tools can record failures/HOLD, but no general application gate requires proof that every listed mechanical check was invoked; the host must follow prompt policy. |
| Tool failure/missing version holds dependent gate; host remains accountable because v1 has no policy extension. | **Instruction-level and partially represented by guarded gate operations.** | README/Lead prompt say missing required checks must HOLD; `gates.py` blocks invalid gate records. Direct host bypass is expressly not prevented. |

**Item 10 disposition:** Review complete. The implementation largely follows the Pi-native target and provides useful local deterministic mechanics. It does **not** satisfy the blueprint’s deployment verification or security exit criteria. The strongest concrete safety boundary is the typed Beads extension’s host/session binding and model-only exposure; this is not general filesystem/network confinement and must not be generalized to all children or `codemode`.

**Next item:** §11, Agent prompts and contracts.

---

## Audit item 11 — Agent prompts and contracts (§11)

**Review completed:** 2026-11-24 (item 11; after item 10 and before item 12). **Item verdict: SUBSTANTIALLY PROMPT-ENCODED, NOT FULLY CONFORMANT OR RUNTIME-VERIFIED.** The Lead, Advisor, and Worker prompts exist and cover most role/authority boundaries, gates, evidence, review, bounded work, and result contracts. Prompt-layer instructions are not enforcement; broad readiness assessment, mandatory delegation/reason-to-retain, and effective capabilities remain gaps noted in items 2–4/10. No child prompt was smoke-run under actual subagent resolution.

### §11.1 Research Lead host prompt

| Template requirement | Finding | Evidence / limitation |
|---|---|---|
| Host-only role loaded with `--append-system-prompt`; Lead owns lifecycle, work, state, artifacts, decisions, human escalation. | **Present and aligned.** | `.pi/agents/research-lead/agent.md` identifies the main session as Lead and directs startup through `research.py lead`; `research.py` appends the prompt and records the project binding. |
| Assignments and specialist/service routing; review and accept child work; keep judgment with Lead; operator-approved pool only outside fixed scopes. | **Partially matches.** | Prompt describes all seven roles, fixed-roster-first, pool approvals, separate acceptance, and OKF judgment/mechanics boundary. It omits the full mandatory delegation rule for every meaningful READY handoff and rationale for meaningful direct work; see item 3. |
| Maintain project records, budgets, and checkpoints; avoid fabrications; distinguish facts/inference and preserve negatives; do not advance before reviews/evidence. | **Mostly encoded; several implementation limitations.** | Prompt covers facts/inference, negative/contradictory evidence, gate routes, director updates, and `project-state`/Git. External budget tracking, per-gate/cycle commit enforcement, and readiness assessment are incomplete (items 1, 3, 8). |
| Advisor consultation discipline: precise question, compact brief, artifacts/alternatives/constraints/output, fresh context and inspect findings. | **Basic instruction present, full package contract absent.** | Lead prompt asks for a decision-oriented brief, cited artifacts, fresh consultation, and inspection. No §6 package schema/quality-check tool exists (item 6). |
| Human authority and fail-closed/escalation boundaries. | **Strongly encoded; not hard policy.** | Prompt covers DECISION-REQUIRED/FYI, ambiguity, stop, blocker, and gate HOLD/escalation; state tools record some related entries. No direct-host permission extension prevents bypass. |
| Complete §3.2 readiness and §3.3–3.5 task-routing/delegation duties. | **Not fully covered.** | Lead prompt includes gate readiness and `READY` for assignment dispatch, but not the seven-dimension assessment, READY/INVESTIGATE/CONSULT/BLOCKED classifier, explicit uncertainty taxonomy/triggers, or mandatory delegation/no-delegation rationale. |

### §11.2 Research Advisor prompt

| Template requirement | Finding | Evidence / limitation |
|---|---|---|
| Canonical `research-advisor`, fresh context, read-only allowlist, replace prompt, no write/edit/shell/subagent, strong independent model. | **Declared in frontmatter; deployed effectiveness unverified.** | `.pi/agents/research-advisor/agent.md` declares `tools: read, grep, find, ls`, `defaultContext: fresh`, `inheritSkills: false`, and `model: gpt-6.2-sol`; prompt prohibits mutation/execution/delegation. Resolved provider/model, aliases, and effective tools have no live attestation. |
| Mission, consultation modes, critical critique, request primary evidence, no ownership transfer or self-confidence-based agreement. | **Substantially encoded.** | Advisor prompt implements Modes A/B/C, enumerates review failure classes, says approval is not proof, binds verdict to artifacts, and allows bounded evidence requests. No quality benchmark/real review is available. |
| Return §4.4 structured verdict and findings for required gates; distinguish advice from verdict. | **Contract encoded and checked locally.** | Prompt provides JSON shape and meanings; `gates.py validate_verdict` checks shape/target. Gate and advice storage are distinct. Live response schema behavior remains unverified. |

### §11.3 Engineering Worker prompt

| Template requirement | Finding | Evidence / limitation |
|---|---|---|
| Bounded writer role; host retains scope/plans/decisions/transitions/acceptance; exact package only. | **Strongly encoded.** | `.pi/agents/engineering-worker/agent.md` restricts edits to allowed paths, contains the plans-only exception, forbids governance changes and research decisions, and requires exact Beads/assignment/revision/attempt/base/input/scope/criteria/commands/budget. |
| Worker invokes only named architects nested in the package; never Advisor, pool, Lead, later-stage coordinator; bounded depth and skills. | **Prompt and frontmatter present; runtime edges unverified.** | Frontmatter declares both skills, explicit `subagent`, `allowNestedSubagents: true`, `maxSubagentDepth: 2`, fresh context. Prompt permits only the three architects and prohibits Advisor/Lead. No nested runtime dry run or denial probe was performed. |
| Execute only authorized checks and return observed status/evidence, `SUCCESS/PARTIAL/BLOCKED`, deviations and `not_run`; no heartbeat or false pass. | **Contract present; actual returns absent.** | Worker prompt tracks exact commands/outputs and explicit not-run reasons; reports partial/blocker and says run completion is not acceptance. No Worker child result has been inspected. |
| Suggested frontmatter/tool set includes command execution, bounded write access and nested subagent tool; loading provider is separate. | **Mostly matches at declaration level.** | Worker declares `read/grep/find/ls/edit/write/bash/subagent`; no `codemode` entry is declared in this role’s current allowlist, although `bash` supplies scoped command execution and this was not shown necessary for the Worker contract. Effective tool list and all runtime limits remain unverified. |

**Item 11 disposition:** Review complete. The prompts are detailed and generally align with the specified authority contracts. They do not substitute for actual tool/provider inspection or OS confinement. The main Lead prompt is notably less complete than the blueprint templates on readiness and mandatory delegation, and no role-level behavior has been demonstrated with live child runs.

**Next item:** §12, Evaluating the research-agent system.

---

## Audit item 12 — Evaluating the research-agent system (§12)

**Review completed:** 2026-11-24 (item 12; after item 11 and before item 13). **Item verdict: NOT EMPIRICALLY EVALUATED; OPERATIONAL FIXTURE COVERAGE IS PARTIAL.** The repository has useful unit/integration and fault-oriented tests for ledger/gate/Beads mechanics. They do not evaluate research quality, Advisor false acceptance, collaboration benefit, end-to-end success, latency/cost, or actual recovery with live child runs. §12.4's list is not covered end-to-end.

### §12.1–§12.3 Benchmarks, system variants, and dimensions

| Requirement | Finding | Evidence / limitation |
|---|---|---|
| Benchmark externally assessable assignments, including ambiguous/conflicting evidence and correct inconclusive decisions. | **Not performed.** | No Director-authorized research question, data, or benchmark run exists. `todos.md` leaves the real research pilot open. |
| Compare variants A–E (Lead only; mandatory reviews; uncertainty consultations; curated context; bounded Worker). | **Not performed / no trial harness.** | No variant execution, randomization, independent scoring, or comparison dataset is present. `todos.md` lists system-variant evaluation as open. |
| Measure research quality, collaboration, operational performance, context sufficiency, cost/latency, recovery, trace completeness using independent criteria. | **Not implemented as an evaluation program.** | Local tests report code/state mechanics only; no scoring rubric, blinded external assessor, consultation-value instrumentation, per-role token/cost data, latency metrics, or false-acceptance metrics are produced. The paired analysis helper is not an evaluation of the agent system. |

### §12.4 Failure-injection scenarios

Statuses below distinguish local guard presence from a test that demonstrates it; local fixture output is not live-agent evidence.

| # | Scenario | Implementation/test finding |
|---:|---|---|
| 1 | Lead misunderstands question → detects ambiguity and consults. | **Not tested; readiness/uncertainty classifier missing** (item 3). |
| 2 | Lead selects invalid methodology → Advisor rejects/revises. | **Prompt/route machinery only; no end-to-end methodology rejection test or live review.** |
| 3 | Advisor approves incorrect code → automated tests prevent premature success. | **Partial structural guard:** acceptance requires successful recorded checks; records are self-reported and not process-attested. No false-Advisor-approval experiment. |
| 4 | Worker claims unrun checks passed → Lead reruns/rejects. | **Partial:** result schema distinguishes exit result/not-run and acceptance checks exit codes; no live Worker deception/rerun scenario. |
| 5 | Fixed-role task, role unavailable → no pool substitution; fixed-role recovery. | **Prompt-only / not tested.** Assignment ledger does not infer task scope-to-role mapping. |
| 6 | Pool unapproved/changed/ambiguous/unverifiable → no launch, even smoke. | **Partial fixture coverage:** `pool_profile` rejects mismatched model and prohibited indirect delegation; it compares supplied records and does not resolve runtime profiles. No live launch refusal test. |
| 7 | Pool returns wrong IDs, stale inputs, missing evidence, or PARTIAL. | **Structural checks present; partial fixture coverage.** `evidence.py` binds IDs/pins, labels late results, requires verification, and refuses acceptance of non-SUCCESS/late results. No real pool response was tested. |
| 8 | Resume with dispatch intent/no run ID. | **Fixture-tested state path:** `launch_unknown` blocks blind retry and `prove-non-dispatch` is explicit; no actual Pi restart/correlation evidence. |
| 9 | Replaced attempt returns late or mutation receipt is replayed. | **Mechanics and fixture tests present:** late output stays on original attempt; operation replay cannot create a fresh launch receipt. No live interruption run. |
| 10 | Accepted result superseded after downstream use. | **Fixture-tested:** old record stays, consumer chain is invalidated, stale reliance flags are surfaced. No real evidence chain. |
| 11 | Beads closed without available evidence or stop between integration and closure. | **Partially tested against real disposable Beads DB:** guarded close requires matching ledger receipt; adapter integration tests interruption before close and exact reconciliation. No live multi-store process interruption. |
| 12 | Accepted workspace change but process stops before integration record. | **Fixture-tested mechanics:** write availability requires integrated checkpoint and exact committed hashes. No automatic quarantine/live Worker mutation. |
| 13 | Query tasks then retrieve historical assignment revision. | **Source support; no explicit targeted regression identified.** Exact Beads IDs and ledger revision retrieval exist; search remains lexical/current-task state. |
| 14 | Optional pool timeout vs mandatory Advisor failure; independent work continues. | **Partial separation by design; composite test not found.** Ledger tracks assignment recovery separately from gate HOLD, prompt scopes dependents. The tracker says independent work during another recovery was exercised, but no test in `tools/research-ops` names/asserts the optional-timeout-plus-mandatory-Advisor case; the generic concurrent-reservation test is not equivalent. |
| 15 | Protocol approved/readiness absent or baseline coverage lapses. | **Partial fixture coverage:** phase-specific approval and stale-manifest rejection exist; readiness reuse/drift and full persisted runtime artifact checks remain explicitly open in `todos.md`. |
| 16 | CYCLE_GATE requests plan-changing revision; draft not charged; approved replan charged once even after resume. | **Partial fixture/source coverage:** code leaves draft routes in cycle and charges only legal `approve/replan`; tests cover cycle charge/replay. A full interrupted/resumed draft→review→charge path is not demonstrated. |
| 17 | Cap/stagnation with each CYCLE_GATE verdict. | **Partial fixture coverage:** final-cycle achievement, in-plan repair, and block precedence are tested. Not all approve-unmet/revise-plan-at-cap/inconclusive/no-verdict paths are individually covered; no real progress evidence. |
| 18 | Advisor lacks context → requests primary evidence. | **Prompt-encoded only; no consultation test/run.** |
| 19 | Advisor gives contradictory advice → record conflict and empirically resolve. | **Instruction-level; no conflict record resolution or experiment test found.** |
| 20 | Experiment returns negative result → preserve/report honestly. | **Prompt-level only; no empirical results or negative-result pipeline.** |
| 21 | Upward message lacks tag/record → tag and record. | **Prompt and decision tag schema present; no message/record enforcement or scenario test.** |
| 22 | Director requests mid-run status → answer from records or disclose missing record. | **Prompt-only; no director Q&A run.** |
| 23 | Ambiguous director reply → ask one question, read back, close/supersede and refresh brief. | **Prompt/state concepts present; no communication workflow/test.** |
| 24 | Writer returns `needs_review` → triage, never override/fabricate. | **Prompt and validator contracts present; no live writer result/triage test.** |
| 25 | Reader reports gaps → investigation tasks; gates cannot rely on missing evidence. | **Prompt-level; no reader run.** Evidence-use pins can gate a recorded consumer, but no reader-gap workflow was tested. |
| 26 | Malformed/stale service result or failed validator at gate → HOLD. | **Partial local tests:** malformed/stale Advisor verdicts HOLD; validators exist. Required OKF service results/precheck are not automatically coupled to gate transition and no stale service response injection was tested. |
| 27 | Inconsistent experiment results → investigate variability/validity. | **Not tested; no experiment runner/result set.** |
| 28 | Lead/Pi interruption → new host reloads project, reconciles state/artifacts, recovers or relaunches Advisor appropriately. | **Fixture/state procedures only; live interruption recovery open.** README documents recovery; no actual Pi child run or host restart was correlated. |
| 29 | Worker interrupted after file mutation before acceptance → reconcile base, quarantine unaccepted changes, reverify. | **Partial ledger safeguards; no actual quarantine/live Worker test.** Workspace base/head, effect state, and checkpoint verification exist; quarantine and process termination are operator/host procedures. |
| 30 | Project-wide resource budget exhausted → HOLD and ask human. | **Not implemented/tested for project-wide spend.** Only local cycle/attempt limits exist; token/API/compute budgets and monitoring are open. |
| 31 | Retrieved document contains malicious instructions → treat as untrusted. | **Partial:** OKF reader/writer prompts explicitly treat bundle content as untrusted; no comprehensive Lead/Worker policy or malicious-content test was found. |
| 32 | Evaluation data contaminated → flag threat and stop affected claims. | **Not implemented/tested:** no dataset provenance/contamination detection or scientific stop test. |

**Item 12 disposition:** Review complete. Local implementation tests substantiate a subset of mechanical failure handling, not the complete §12.4 behavior suite. Fixture tests do not demonstrate independent scientific review, model behavior, security confinement, paid-run recovery, or research-system effectiveness. Formal system-quality evaluation is deliberately deferred until real runtime use yields evidence; this is a later evaluation objective, not a prerequisite to authorized, safety-gated iterative development.

**Next item:** §13, Implementation roadmap.

---

## Audit item 13 — Implementation roadmap (§13)

**Review completed:** 2026-11-24 (item 13; after item 12 and before item 14). **Item verdict: FOUNDATION WORK IS REAL; NONE OF THE MILESTONE EXIT CRITERIA IS FULLY EVIDENCED.** Several milestone implementation tasks and fixture checks are complete, but the roadmap’s behavioral exits require live role execution, confinement/pilots, reproducible research evidence, or measured system evaluation that is absent. Checklist completion is not equivalent to milestone completion.

| Milestone | Implemented/source evidence | Exit-criterion assessment |
|---|---|---|
| **1 — Lead, Advisor, Worker, services, Beads/ledger, pool** | All role definitions exist; Lead exclusion and launcher exist; Beads adapter and managed ledger are implemented; real disposable Beads SQLite, Pi CLI/SDK tool-registration, and Git-checkpoint tests pass. Static pool-profile comparison exists. | **NOT MET.** No live invocation of Advisor/Worker/seven roles, resolved model/override evidence, Worker→three-architect dry run, single-writer Worker run, approved pool run, approved `codemode`/scoped write, runtime pool refusal, or actual interrupted dispatch/close evidence. The required behavior and confinement evidence are explicitly open in `todos.md`. |
| **2 — Host-led lifecycle discipline** | Lead prompt has dual-loop/gate instructions; `gates.py`/ledger guard phases, routes, counters and stop predicates; synthetic review fixtures cover key cases. | **PARTIAL / EXIT NOT MET.** The broad task-readiness classification and explicit uncertainty-trigger list are missing. All Advisor outputs and stage outcomes in tests are simulated; no real research exercise shows the Lead loops through stages/gates or escalates correctly. No live host-session resume was performed. |
| **3 — Research execution tools and confinement** | Project bootstrap, source/artifact paths, manifests/freshness checks, tests, paired analysis helper, and role tool declarations exist. | **NOT MET.** No trusted literature/search integration or full experiment runner, isolated execution/sandbox, direct/`codemode` denied-capability probes, approved extension/MCP scoping, or small end-to-end empirical study. The runbook explicitly says prompt permissions are not confinement. |
| **4 — Scientific evaluation** | A narrow deterministic paired-bootstrap reference analyzer emits provenance and a limitation-labeled draft; local constructed-observation test passes. | **NOT MET; deliberately deferred.** The Director intends to accumulate evidence through actual runtime development rather than require a separate up-front scientific pilot. No real raw results, claim-to-evidence matrix, confirmatory evidence, full statistical rubric, reproducible report, or final manifest-backed result exists yet. The analyzer is not a model-performance result; formal evaluation remains necessary before effectiveness claims. |
| **5 — Recovery, budgets, consultation optimization** | Local project-state resume/status/operation receipt mechanics, assignment recovery records, and runbook exist; simulated interruption and Git integration tests cover parts. | **NOT MET.** No real host/Advisor/Worker recovery, unaccepted workspace quarantine probe, external quotas/resource accounting, context package generation, selective evidence expansion study, decision reuse, cost/token attribution, or measured consultation-efficiency result. |

**Item 13 disposition:** Review complete. The milestone descriptions remain a valid target roadmap, but the current system is best described as **implemented local operational scaffolding plus prompts and synthetic tests**, not as having passed Milestone 1 or 2 behavioral exits and not as having completed Milestones 3–5.

**Next item:** §14, Worked example.

---

## Audit item 14 — Worked example (§14)

**Review completed:** 2026-11-24 (item 14; after item 13 and before item 15). **Item verdict: ILLUSTRATIVE SPECIFICATION, NOT AN IMPLEMENTED RESEARCH PROJECT.** The prompting/peak-performance question is a worked example of the required planning→implementation→evaluation→analysis→reporting behavior, not a claim that this research was run. No project artifacts or empirical results for this example were found.

| Example element | Implementation status |
|---|---|
| Research question: determine whether prompt optimization changes semantic specification, elicitation, adaptation, or reasoning strategy. | **No active charter/project.** No question, objectives, hypotheses or resources were authorized/recorded for this topic. |
| Planning: literature, competing causal hypotheses, controlled task families, frontier model choices, interventions, baselines/metrics, protocol and Advisor critique. | **Not performed.** Prompts support some planning/review duties, but no literature/experiment plan or Advisor review exists. |
| Implementation: bounded prompt-variant generator package, semantic-equivalence tests, Worker observed output, Lead acceptance, separate readiness review. | **Workflow pattern partially supported by ledger/gates; no WORK-001 code/package or real Worker run.** |
| Evaluation: benchmark metrics, per-attempt grader repair within same plan, comparisons across task difficulty, cost and uncertainty. | **Not run.** Only the narrow constructed-data paired-analysis helper exists; no model calls or raw benchmark data. |
| Analysis: interpret competing hypotheses, diagnose confounds, Advisor review, cycle decision and approved replan vs in-plan repair, human authority for charter change. | **State/gate mechanics and prompt rules partially encode this; no observations or cycle decision exist.** |
| Reporting: separate observations/interpretations/speculation, limitations, implications, code/config/raw data/manifests. | **No report or claim-evidence artifacts.** Prompt guidance and workspace directories do not demonstrate a completed report. |

**Item 14 disposition:** Review complete. The example remains a useful target behavior, but it is not evidence of implementation or system efficacy. Any future result about prompt variation must be evaluated independently and must not use this illustrative scenario as if it were observed data.

**Next item:** §15, Final design decisions.

---

## Audit item 15 — Final design decisions (§15)

**Review completed:** 2026-11-24 (item 15; final sequential item). **Item verdict: ARCHITECTURAL CHOICES ARE MOSTLY REFLECTED IN THE STATIC DESIGN; MANY OPERATING REQUIREMENTS ARE INCOMPLETE.** This section consolidates earlier specifications rather than adding a separate implementation. The final principle (reliable research per human attention/computational resources) has not been empirically measured.

| Final decision | Finding |
|---|---|
| One Lead host plus seven named children; fixed-role-first, Lead-only operator-approved pool. | **Definitions/config and pool comparison exist; approval, routing coverage and actual discovery remain unverified.** |
| Lead is main Pi host; Advisor read-only; Worker bounded writer with depth-2 architect consultations; specialists read-only/domain-only. | **Prompt/frontmatter definitions align; runtime permissions/nested edges are not attested.** |
| Lead retains primary ownership, implementation acceptance, research decisions and director communication. | **Prompts and ledger separation encode this; no live acceptance or director interaction has been tested.** |
| Same `subagent` tool, no second orchestration framework/workflow engine in v1. | **Matches the checked-in architecture and launcher.** |
| Mandatory gates are instruction-level and require a separate policy extension for non-bypassability. | **Explicitly documented and accurately not claimed as enforced.** Local transition tools guard only ledger-mediated routes. |
| Structured readiness records, not arbitrary confidence numbers. | **Not satisfied for general meaningful tasks:** assignment READY exists, but the required task-readiness classifications/dimensions are missing (items 3, 8). |
| Compact consultation packets with expandable evidence and fresh Advisor context. | **Partially prompt-encoded; no package schema/quality validator/cost instrumentation, and live context is unverified (item 6).** |
| Versioned project artifacts are durable truth; child runs are execution history. | **State/manifest/ledger scaffolding aligns; no populated project or full canonical artifact hub exists (item 7).** |
| Executable checks, provenance, independent scientific validation; Advisor agreement is not proof. | **Mechanical checks and deterministic analysis helper exist; independent empirical validation/system study does not (items 9, 12).** |
| Human involvement for authority/material unresolved issues. | **Prompt/state tags exist; actual director decision and stop-control path is untested.** |
| Suggested stack: Pi/Subagents, Git, project state/artifacts, analysis/check tools, literature sources. | **Core Pi/Beads/ledger/test pieces are present; literature integrations, isolated experiment execution, external artifact storage and usage quotas are incomplete (item 10).** |
| Add policy, persistence, or UI expansion only when evaluation justifies it. | **No premature dashboard/second workflow framework found. Whether future additions are justified remains unmeasured because system evaluation has not run.** |
| Maximize scientifically reliable research per human attention/computational resources. | **Aspirational objective, not measured or demonstrated.** Resource accounting and empirical research-quality/cost evaluation remain open. |

**Item 15 disposition:** Review complete. The final decisions are consistent with the current high-level architecture, especially host ownership, fixed roles, no second workflow engine, and the candid instruction-level gate caveat. The implementation does not yet realize or verify the complete target, particularly readiness, controlled delegation, security, durable project artifacts, complete scientific work, external budgets, and measured effectiveness.

---

## Overall audit conclusion

All **15 top-level blueprint sections** have now been reviewed sequentially. “Reviewed” means the requirements were audited and recorded; it does not mean they are implemented. No complete top-level section can be certified as **fully implemented and verified** against every clause in its scope because each includes missing or unverified requirements, especially live deployment, scientific, security, or operational behavior.

### Strongest verified implementation areas

- Typed, explicitly bound Beads v0.49.6 SQLite tools and real disposable-DB integration tests.
- Managed project ledger with serialized revisioned writes, operation receipts, assignment/result/acceptance separation, evidence hashing, Git-checkpoint validation, supersession invalidation, and fixture coverage.
- Phase-specific gate validation and route guards with simulated-review regression tests.
- Bootstrap/launcher, static preflight, operator-attestation validation, OKF validators/check helpers, and deterministic paired-analysis support.
- Research-role prompts and definitions that encode substantial ownership, review, and bounded-work requirements.

### Highest-priority conformance gaps

1. General seven-dimension task-readiness assessment and READY/INVESTIGATE/CONSULT/BLOCKED routing, explicit uncertainty taxonomy and mandatory consultation triggers.
2. Mandatory delegation of suitable READY tasks and durable rationale when meaningful work is retained by the Lead; no route classification engine exists.
3. Real seven-role smoke runs, effective provider/model/override and tool inspection, fresh-context/schema verification, and Worker→architect nested-path evidence.
4. Host/tool-layer file/command/network/`codemode` confinement, runtime profile resolution, and interrupted-dispatch/process-exit/effect-reconciliation probes. Prompts and Pi tool allowlists are not a sandbox.
5. Complete project artifacts: planning/evaluation/analysis/report deliverables, empirical experiment runner/raw results, claim-evidence matrix, and confirmatory data. The current project tree is not initialized.
6. Project-wide compute/model/API/external-action budgets, usage/cost accounting, hub mutation serialization, and full schema validation.
7. System-level research-quality, collaboration, recovery, cost/latency, and consultation-effectiveness evaluation is **deferred until real runtime use yields a useful evidence base**. Preserve operational traces during development; do not make effectiveness claims before formal evaluation.

### Sequencing clarification — empirical evaluation deferred

**Report update timestamp (UTC):** 2026-11-24T07:12:31Z. The Director clarified that a separate scientific/system-efficacy pilot should not be required before iterative runtime development. The intended approach is to use authorized real work to run the agent team, debug failures, analyze observations, and improve it continuously. This audit therefore treats the absence of a scientific pilot as **deferred evaluation**, not as a blocker to otherwise authorized, safety-gated development. Preserve run/configuration/results/failure/cost information during that development where available; distinguish development observations from confirmatory evidence and make no research-quality or cost-effectiveness claims until an appropriate formal evaluation is performed. This deferral does not waive the independent runtime safety prerequisites: role/tool/model verification, confinement, budgets, and the single-writer/approved-pool controls remain required before enabling those capabilities.

### Evidence and scope limitations

- The exact source checkout was dirty before audit start (see Tracking metadata); findings are based on the observed working tree plus local tests. The separate `.pi` checkout contains its own package dependency edits.
- CodeGraph indexing is unavailable for this checkout; implementation review used direct file reads/search, not graph-based discovery.
- Local tests establish only their exercised fixtures. Research-op tests simulate child run/status/gate observations; Pi bootstrap exposure is credential-free and Beads tests use disposable databases. No live child agents, paid provider calls, real deployment confinement probes, or authorized scientific study were performed.
- Blueprint sections 14 and technical references are illustrative/contextual; references are not treated as executable acceptance requirements. The worked example was checked for corresponding implementation evidence but was not run.

**Final status:** Static architecture and operational scaffolding are substantial; overall blueprint conformance is **PARTIAL / NOT YET DEPLOYMENT-VERIFIED / NOT SCIENTIFICALLY VALIDATED**. The formal scientific/system evaluation is intentionally deferred until real runtime development accumulates evidence; it is not an up-front prerequisite for iterative debugging. Keep delegation disabled until the applicable deployment/security checks and single-writer (then approved pool) pilots pass. Do not claim research quality or system effectiveness until the deferred empirical evaluation is completed.
