# Proposal: Research Lead as Continuous System Steward

## Tracking metadata

- **Created (UTC):** 2026-11-24T07:27:25Z
- **Status:** Proposal for Director review; **not approved or implemented**.
- **Review:** Recommendations from two read-only `harness-architector` consultations have been incorporated below. The consultations reviewed the proposal and named design/audit documents; they did not inspect source code or run tests.
- **Related design authority:** `blueprint-v1.md` v1.4. This proposal suggests an amendment (e.g. v1.5); it does not silently override the current blueprint.
- **Related audit:** `blueprint-implementation-audit.md` (sequential implementation-coverage review).
- **Project root checkpoint:** branch `main`, HEAD `d345f942feb8fd34ef681c20dfebdd242026a58b`; pre-existing changes before this file: modified `todos.md`, untracked `blueprint-implementation-audit.md`.
- **Pi configuration checkpoint:** branch `intell-ocr`, HEAD `18f4c327b6aed209ee153524928391910bd9cabb`; working tree clean.
- **Post-consultation update checkpoint (UTC):** 2026-11-24T07:47:18Z. Project root remained at HEAD `d345f942feb8fd34ef681c20dfebdd242026a58b`; working tree contained modified `todos.md` plus untracked `blueprint-implementation-audit.md` and this proposal. `.pi` remained at HEAD `18f4c327b6aed209ee153524928391910bd9cabb` and clean.
- **Playbook incorporation checkpoint (UTC):** 2026-11-24T08:26:30Z. Project root remained at HEAD `d345f942feb8fd34ef681c20dfebdd242026a58b`; working tree contained modified `todos.md` and untracked `blueprint-implementation-audit.md` plus this proposal. `.pi` remained at HEAD `18f4c327b6aed209ee153524928391910bd9cabb` and clean.
- **Overview addition checkpoint (UTC):** 2026-11-24T08:36:29Z. Project root branch `main`, HEAD `11ee024a6eeae614753ec186b015f776bacb5b98`; the proposal is untracked. `.pi` branch `intell-ocr`, HEAD `18f4c327b6aed209ee153524928391910bd9cabb`; working tree clean.
- **No commits were created for this proposal.**

## Overview

### Intended outcome

The Research Lead remains the main Pi host and owner of research work, while also taking responsibility for continual, evidence-driven development of the research-team system. The Lead observes problems during authorized real work, diagnoses their effect, proposes and tests bounded improvements to prompts, tools, scripts, tests, or orchestration, and follows the approved review/release path. This is a **bounded system-steward** model—not an unrestricted, recursively self-modifying agent, a new standing role, or a second workflow engine.

The research loop and system-improvement loop are related but distinct. A runtime failure may motivate a system change, but changing the system does not by itself change a research plan, satisfy an Advisor gate, or establish a scientific result.

### Target architecture

```text
Director
  ├─ sets research goals, operating envelope, budgets and protected approvals
  └─ retains authority over charter changes, protected releases and stop decisions
          │
          ▼
Main Pi session: Research Lead (pinned version N)
  ├─ Research loop: plan → implement/evaluate → analyze → report
  │    └─ existing fixed roster and separately approved pool, within verified limits
  └─ System-improvement loop: observe → triage → propose → authorize
       → implement isolated candidate → verify/review → release/rollback
          │
          ├─ records tasks, runs, evidence, decisions and checkpoints
          └─ may consult existing fixed specialists; advice is not release approval
          │
          ▼
Operator-controlled promotion of an approved, version-pinned candidate
          │
          ▼
New Lead/agent/tool version N+1; monitor first eligible use and retain rollback
```

The Lead may author and test changes, but its permission to edit is separate from permission to promote. Routine changes start in an isolated workspace; the approved release, promotion credentials, protected controls and independent approval record stay outside the candidate session’s write authority. Changes to role authority, access/confinement, gates, validators, budgets/stop controls, pool/model approvals, evidence policy, or charter-level objectives require explicit Director approval and independent verification. Plan-level research changes use the existing CYCLE_GATE/PLAN_GATE process.

### Example: improving recovery after an uncertain Worker timeout

If a Worker times out and no reliable run ID is recorded, the Lead first keeps the attempt unresolved (`launch_unknown`), blocks unsafe retry, and checks for workspace/external effects. A timeout does not prove process termination. It records the pinned agent/runtime version, task/attempt IDs, exact observation, affected dependents, and what remains unknown. If repeated use reveals a narrow diagnostic gap, the Lead can propose a low-risk trace improvement, replay the incident in a disposable workspace, and test both a normal completion and an interrupted write. A change to retry authorization or a gate is protected and cannot be promoted by the Lead itself. After approval, the new version runs in a later pinned session; first-use results are monitored and any affected evidence/reviews are revalidated.

### How improvement opportunities are assessed

Assess consequences, not symptoms. A request for more evidence may be proper review behavior; a stale-manifest rejection may be a safeguard working correctly; fewer consultations or more completed tasks are not improvements if defects escape or hard cases are dropped. For each consequential issue, trace:

> expected behavior → observed divergence → downstream effect/exposure → suspected cause → smallest check that distinguishes a plausible alternative

Triage by distinct impact dimensions—validity, output quality, recovery, cost, and human attention—without combining them into one score. Use **contain now**, **fix next**, **investigate with a bounded check**, or **defer/watch with a reopening trigger**. Safety/authority concerns and uncertain external effects HOLD the affected work before diagnosis or retry.

At task intake, preserve the population of meaningful work (direct, delegated, deferred, declined, and never-started where known). Review all known high-risk cases; use a prospective, risk-stratified sample for ordinary work, retain eligible/selected/reviewed denominators, and never replace difficult cases with clean ones. A small two-week/five-case cap can be a workload starting point only—it is not a statistically justified sample size. The current ledger does not capture every such task state; record this in existing Beads/ledger or linked artifacts before claiming representative coverage, rather than creating a parallel tracker.

Keep three evidence sets distinct:

- **Incident replay:** reproduce or diagnose a specific failure; not a failure-rate estimate.
- **Regression set:** verify fixed expected behavior and guard against regressions; passing cases show only those cases.
- **Confirmation set:** evaluate a frozen candidate against a credible baseline on unseen representative work, with predefined sampling/scoring/stopping rules. This is needed for broad effectiveness claims, but is deferred until runtime use provides a useful evidence base.

Promotion evidence answers whether a specific change passed its required checks; it does not prove that the overall system produces better research. Preserve development observations, local verification, and later confirmatory evidence as separate categories.

### Status of this vision

This is a proposed target, not a description of current runtime capability. The existing repository has role definitions, a Lead prompt, assignment/gate ledgers, local tests and a paired-analysis helper. It does not yet demonstrate live role resolution, full confinement, general task-intake coverage, or an empirical improvement in research quality or cost. Apply the existing capability-specific safety prerequisites before using delegated write, pool, or `codemode` paths.

## Executive proposal

Expand the Research Lead’s remit so it is accountable not only for operating research projects, but also for **continual in-progress development of the research-team system**: use runtime experience to identify defects and friction, propose and implement bounded improvements to prompts, tools, scripts, tests, and orchestration, verify the changes, and improve the system iteratively.

Keep the Research Lead as the main Pi host and sole accountable owner. **Do not add a new standing lifecycle role or a second orchestration framework.** The important limitation is that system stewardship must not give the Lead unilateral authority to weaken the safeguards or approve its own consequential control-plane changes. Routine improvements can be autonomous within a Director-approved envelope; changes to authority, security, budgets, gate semantics, or research success criteria require separate review/approval.

The intended development mode is **learn from authorized real runtime use**, not require a separate large scientific-efficacy pilot before the system can be debugged. Capture useful operational evidence as use occurs. Defer formal system-effectiveness evaluation until there is a meaningful evidence base, and make no efficacy or cost-effectiveness claims before that evaluation.

## Motivation and expected benefits

These benefits are **hypotheses**, not demonstrated results:

- Shorten the loop from a real operational failure to a tested correction.
- Prevent recurrent problems by converting failures and workarounds into regression tests, prompt/tool improvements, and durable operational guidance.
- Improve assignment quality, recovery, traceability, and usability based on observed—not merely anticipated—friction.
- Reduce repeated rework and unnecessary consultation or tool use, if usage evidence shows those costs can be reduced without harming research quality or safety.
- Keep the system aligned with the work it is actually being asked to do, while preserving explicit authority boundaries.

No benefit should be inferred merely because the Lead changed its prompts or tools. Improvement must be assessed against recorded failures, regressions, accepted outputs, cost, latency, and evidence quality.

## Feasibility assessment

### Technically feasible

The repository already has a host Lead prompt, fixed-role definitions, a Worker, Beads and a project evidence ledger, Git/checkpoint support, deterministic validators, a launcher, and local tests. A Lead host with appropriately configured tools can in principle maintain these artifacts and submit changes for verification. Pi prompts and agent definitions are ordinary versioned files.

### Not safe as unrestricted self-modification

The current blueprint explicitly treats lifecycle gates as instruction-level rather than non-bypassable. The audit also found no general OS-level confinement and no way for the project ledger to authenticate all runtime claims. If the Lead may freely change its own authority, tool allowlists, gate validators, budget limits, or the tests that judge those changes, it can create a self-approving loop. A prompt instruction alone is not an adequate safeguard against that failure mode.

### Overall assessment

**Feasible with bounded autonomy and protected control-plane review.** The operational benefit is plausible and the implementation path is incremental. Unrestricted authority to rewrite all of its own rules and deploy those changes without review is not recommended.

## Proposed authority model

Authority is determined by the **effect of a change**, not just by its filename. A prompt edit can change permissions or gate behavior and must be classified accordingly.

| Change class | Examples | Proposed Lead authority |
|---|---|---|
| **A — Routine improvement within approved policy** | Fix a reporting/diagnostic script; add a regression test for an observed defect; improve non-authoritative documentation; repair an ordinary tool bug without changing permissions, acceptance semantics, research criteria, or the protected test suite. | May specify, implement, and verify a candidate in an isolated development branch/worktree within the named task, workspace, and budget. The Lead cannot waive checks or mark a failed/unrun check as passed. **Initially, an operator promotes/releases the candidate.** Unattended promotion is not authorized unless a later Director-approved, enforceable release policy explicitly lists reversible A-class changes and its checks. |
| **B — Agent behavior within existing authority** | Change task clarity, result formatting, evidence references, consultation behavior, or role prompt wording without changing role authority, gates, tool access, stop policy, or research criteria. Purely editorial changes with no behavior effect may be classified A. | May draft and test a pinned candidate in isolation. Behavioral changes require independent review before rollout; the new prompt applies only in a later version-pinned session, never by silently changing the currently running session. Promotion remains operator-controlled unless an enforceable policy later says otherwise. |
| **C — Protected control-plane or research-authority change** | Change who may invoke agents; tool/OS/network/filesystem access; sandbox/secrets policy; gate rules/validators or evidence acceptance; retry/project-wide budget or stop authority; model/provider approvals; pool profiles; charter-level objectives/success criteria; or evidence/gate policy. | **No unilateral change or rollout.** The Lead may investigate and propose a candidate; implementation of protected policy requires explicit authorization, and promotion of the exact reviewed revision requires a separate Director decision. Require independent verification of affected invariants; the Lead cannot approve its own change. |

Changes that combine classes inherit the most restrictive class. An unclear classification is treated as protected until resolved. The change class is determined by effect, not filename: an apparently editorial prompt edit that changes authority, gates, criteria, or permissions is protected.

### Boundary with active research

System-development authorization is separate from research-project authority. The Lead may recommend new research directions, methods, or metrics, but the Director approves charter-level objectives and success-criteria changes. Plan-level hypotheses, methods, baselines, and metrics may be revised only through the existing authorized CYCLE_GATE `approve/replan` and subsequent PLAN_GATE path; they must not be changed mid-cycle to rescue a result. Before a system release is used in an active research project, pin the exact version, record any version switch, and revalidate affected readiness approvals, evidence pins, manifests, and reviews. A system-release approval is not an Advisor gate verdict, and development observations are not confirmatory evidence.

### Director-held authority remains unchanged

- The Director alone authorizes changes to research objectives/success criteria, additional project-wide resources, and cessation/resumption decisions where the blueprint assigns those powers to the Director.
- The Lead may recommend research directions, methods, metrics, scope, and trade-offs, with evidence and consequences. A recommendation does not become a charter change until the Director explicitly approves it.
- The Lead may not modify budgets or tool permissions to work around an exhausted budget, unavailable approval, or failed safety check.

### Independence and anti-self-approval

- The Lead may author a change and its tests, but cannot treat its own assertion, a child `complete`, or its own test report as independent approval.
- Use executable regression/failure-injection tests for mechanical behavior. For design-sensitive changes, consult the relevant existing fixed specialist (e.g. `harness-architector`) for advice; that advice is not authorization or a gate verdict.
- Protected changes require Director approval and independent evidence that the intended policy change works and unaffected safeguards still hold. Keep protected tests/invariants outside the candidate’s write authority; weakening/removing them is itself Class C and requires explicit Director approval.
- Keep the approved release, promotion credentials, and release mechanism outside the candidate session’s write authority. A worktree separates revisions; it is not a permission boundary. If the separation cannot be verified, the Director or authorized operator must promote the exact reviewed revision outside the Lead session.
- Never let a change rewrite its own historical evidence, success criteria after observing results, or the record of why it was made.

## Proposed continual-development loop

Keep this loop distinct from (but compatible with) the research-project loop:

1. **Observe:** Capture a concrete failure, repeated friction, inefficiency, limitation, or improvement opportunity from an authorized run. State expected behavior and its source, what was observed, and what downstream decision, evidence dependency, time, or task coverage changed. Preserve relevant versions/run/task IDs and uncertainty; distinguish direct observation, agent-reported action, and inference. Treat user data and retrieved content as untrusted input.
2. **Triage:** Decide whether the issue is normal research work, system development, security/authority, or a research-charter question. Classify the change A/B/C and assess validity, output quality, recovery, cost, and human attention separately—do not collapse them into one score. Choose a disposition: contain now; fix next; collect bounded evidence; consult/review; or defer/watch with a reopening trigger. A safety/authority concern or uncertain external effect holds affected work before diagnosis or retry.
3. **Propose:** Write a concise change brief: observed problem and downstream impact, suspected cause separately from evidence, credible alternative, affected components/versions, expected benefit, change class, scope, acceptance checks and guardrails, case selection/coverage, resource cap, and rollback/stop conditions. Do not change the primary research objective to make the system look better.
4. **Authorize:** Apply the approved workspace, data/tool scope, external-action scope, spend/time caps, and stop conditions for that change class. Permit only capabilities whose relevant limits are established; leave unverified capabilities disabled outside disposable exercises. If class C or classification is uncertain, stop before implementation/promotion and ask the Director for authorization. A development task must not consume confirmatory research budget without approval.
5. **Implement in isolation:** Work in a separate branch/worktree or disposable development copy, with a pinned base revision. Preserve the currently approved release and current session prompt; do not hot-edit active governance state. Verify that the candidate cannot write to release credentials, protected controls, or its own independent approval record.
6. **Verify proportionately:** Before inspecting candidate outcomes, pin the baseline and candidate, proposed mechanism, strongest plausible alternative, primary outcome, guardrails, selected cases, budget, and stop rule. Replay the incident and add a nearby case plus a case the fix should not change; keep inputs, model/settings, scoring, and tool versions constant where possible. For stochastic behavior, use bounded matched cases/repeats and record per-case differences. Use targeted regression/smoke tests for behavior changes and failure injection when changing failure/recovery behavior. For Class C, a non-author must inspect the exact diff and independently run/observe critical checks against a protected baseline. Verify both the intended change and safeguards meant to remain. A few passing cases support only those cases, not broad efficacy.
7. **Review and release:** Obtain the review and Director approval required for the class. Record whether each key fact is direct observation, agent-reported action, or inference. Commit the accepted candidate with its change-request ID and class. Promotion is a separate operation controlled outside candidate write authority; deploy as a new pinned version, verify resolved prompt/tools/runtime after rollout, and retain the prior approved version for rollback.
8. **Monitor and learn:** On first authorized use of the promoted version, check for recurrence and new failures. Record what changed, what was checked, coverage, limitations, and cost/latency where available. Feed evidence into the next iteration. Do not claim efficacy from one successful run or from the Lead’s self-evaluation.

## Improvement-opportunity playbook

### Observe consequences, not just symptoms

Use natural checkpoints (closeout, gate, failure, or version review) to look at what actually changed downstream. A consultation expansion is not itself a failure; determine whether missing evidence changed a verdict or merely added latency. A stale-manifest rejection may be a safeguard working correctly; investigate whether stale evidence was ever relied on or caused avoidable rework. A timeout is not proof the process stopped; distinguish clean recovery from lost work, unresolved effects, blocked dependencies, or duplicate spend. More task closures or fewer calls are not improvements if hard tasks were dropped or evidence quality fell.

For a consequential signal, reconstruct: **expected behavior → first observed divergence → downstream effect/exposure → suspected cause → smallest check that distinguishes it from a plausible alternative.** If only failures were reviewed, report examples, not a failure rate.

### Define the population before sampling

At the first routing decision, include meaningful work that is direct, delegated, deferred, declined, or never started where known; link retries to the original task rather than counting them as new tasks. Review every known critical/high-risk case involving authority/security, possible validity loss, gate/research claims, or external effects. Unclear risk is treated as high until scoped. Mandatory reviews are never sampled away.

For ordinary work, predefine a risk/task-family stratum and select from stable task IDs using a reproducible ordering that does not use outcome fields. Report eligible, selected, and actually reviewed counts; keep open, dropped, inconclusive, and missing-evidence cases visible. Do not replace difficult selections with clean cases. As a small first learning window, a two-week intake and up to five direct and five delegated ordinary tasks (with a separate small deferred/declined stratum if useful) may cap review workload. These are **workload caps, not statistically justified sample sizes**; adjust prospectively after learning the volume and coverage. If high-risk review capacity is insufficient, narrow intake or HOLD the affected work rather than sampling away the obligation. Do not use the initial sample to claim a population defect rate or system improvement.

The current project ledger does not yet represent every direct/deferred/declined/never-started meaningful task. Before claiming sampling coverage, record this intake population in the existing Beads/ledger or linked project records. Extend an existing record if needed; do not create a parallel tracker.

### Keep three evidence sets distinct

| Evidence set | Question it answers | Use and limit |
|---|---|---|
| **Incident replay** | Can the observed failure be reproduced or its plausible causes distinguished? | Use pinned versions and the smallest authorized reproduction; use inert inputs/disposable environments when side effects or sensitive data are possible. If it does not reproduce, preserve the original observation and the replay limit. It is not a failure-rate estimate. |
| **Regression set** | Does this candidate satisfy a fixed expectation without breaking behaviors meant to remain? | Promote useful replays into versioned tests with explicit expected outcomes; rerun on later revisions. Repeated passes establish only coverage of those cases, not their frequency in usage. Protect critical tests from candidate edits. |
| **Confirmation set** | Does a frozen candidate improve a defined outcome against a credible baseline on unseen representative work? | Freeze candidate/comparator, sampling/scoring, and stopping rules before opening outcomes. Use independent scoring where judgment matters. Cases used to tune the next revision become development data for it; confirmation for that revision requires fresh held-out evidence. Do not repeatedly peek until a result passes. |

### Prioritize without a single scalar

Use disposition bands: **contain now** for possible material harm; **fix next** for a demonstrated consequential failure with a bounded remedy; **investigate** when a bounded check could change the decision; **defer/watch** when evidence/consequence does not justify action, with a reopening trigger. Within a band, consider downstream impact, breadth/recurrence across distinct tasks, evidence strength, and cost/reversibility of the next step. A rare authority/validity failure can outrank frequent minor friction; uncertainty can change the action from “fix” to “check,” but does not erase the risk.

Pair optimization metrics with countermeasures: fewer consultations with missed required triggers/escaped defects; lower cost or latency with end-to-end rework and evidence coverage; more accepted tasks with unsupported claims, dropped work, and task coverage. Distinguish justified inconclusive results from unexplained abandonment. Record unknown spend or missing telemetry as unknown, not zero.

### Minimum per-opportunity record

Record the fields below in the existing Beads task, assignment/decision ledger, or linked versioned development artifact. Link raw traces and diffs instead of copying them; do not make this a second issue tracker.

```text
Opportunity / owner / next checkpoint:
Run, task, attempt, version IDs; approved scope and evidence links:
Expected behavior and source → observed divergence → downstream impact/exposure:
Eligible/selected/reviewed counts and evidence coverage (if sampled):
Direct observation vs agent-reported action vs inference:
Suspected cause; plausible alternative; smallest discriminating check:
Disposition/change class; authorization, budget, stop/resume conditions:
Pinned baseline/candidate; outcome, guardrails, failures/exclusions/not-run:
Evidence tier (development / local verification / confirmation):
Review/release/rollback decision and first-use follow-up:
```

## Evidence to capture during real runtime development

Capture what is available and authorized for each meaningful system-development task:

- Pi, `pi-subagents`, role-definition, model/provider and override versions.
- Project/task/assignment/revision/attempt/run IDs, the exact brief/allowed scope, and the intake population/sampling coverage when applicable.
- Prompt/configuration hashes, relevant tool/capability observations, test versions, baseline/candidate IDs, and changes to active version.
- Observed input class, outputs, failure mode, recovery actions, downstream consequence, acceptance decision, and any regression.
- Test commands and raw outputs, code diff and Git checkpoint; preserve `not run` and negative results.
- Usage/cost/latency data and source/coverage; mark unknown values as unknown rather than estimating silently.
- Whether evidence is development-only, local verification, independently reviewed, or suitable for confirmation.

Logging must respect privacy, secrets policy, approved data scope, and resource limits. Do not copy credentials or sensitive user data into prompts, reports, or permanent memory.

## Measurement plan—deferred, not waived

During development, use practical operational measures as they become available: repeat-failure rate, time to diagnose/recover, accepted-work rate, test regressions, gate/assignment errors, missed triggers/escaped defects, unnecessary retries/consultations, cost and latency per accepted task, task coverage, and trace completeness. Define denominators and coverage before reporting rates. Establish a baseline from actual usage before judging improvement. Development observations are useful for debugging but are not automatically confirmatory research evidence.

After sufficient real usage accumulates, the Director and Lead can define a focused formal evaluation: comparison variants or before/after cohorts, independent scoring, held-out/failure-injection cases, resource measurements, and claims tied to raw evidence. Formal evaluation is required before claims that the system improves scientific quality, is cost-effective, or outperforms an alternative. It is not required merely to begin safe iterative development.

## Prerequisites and staged adoption

1. **Specify policy:** Amend the blueprint to define change classes, approved scope, protected invariants, human approvals, and evidence requirements. Do not infer self-modification authority from a general “Lead owns the project” clause.
2. **Name the first operating envelope:** State the workspace, authorized data and tools, external actions, spend/time caps, and stop conditions. Begin with real authorized work only through capabilities whose limits are established. A host-only or local task may be eligible even while delegated capabilities remain disabled; lack of confinement evidence is not permission to use an unverified Worker, pool, or `codemode` path.
3. **Verify capabilities before enabling them:** Before delegated writes, verify effective roles/tools/models and applicable host/tool-layer confinement, including indirect calls. Start with one writer and recovery checks; enable the operator-approved read-only pool only after its profile and relevant probes pass. Keep release credentials and production promotion outside the candidate session.
4. **Start with bounded development work:** Use an isolated workspace and a routine Class A change. Capture operational evidence from real work; do not begin with self-edits to gate/security policy.
5. **Add protection as evidence warrants:** Extend tests/deployment controls based on observed risks; require explicit Director approval for protected changes and operator-controlled promotion until release enforcement is demonstrated.
6. **Evaluate when evidence is sufficient:** Schedule formal system evaluation after runtime use produces an adequate evidence base and before making effectiveness claims.

## Open decisions for the Director

This proposal is not an implementation authorization. Before adding it to the authoritative blueprint, decide:

1. Which class A changes may the Lead merge without prior approval, and which require a human review even if policy-preserving?
2. Which exact files/policies constitute the protected control plane (at minimum: role authority, tool/runtime permissions, gates/validators, budgets/stop authority, pool approvals, and research objectives/success criteria)?
3. Which disposable/isolated environment and resource budget authorize the first real runtime development iterations?
4. What independent review and rollback evidence is required for prompt/tool/orchestration changes?
5. What accumulated evidence is sufficient to begin the later formal evaluation?

## Recommendation

Adopt the **bounded system-steward** model as a proposed next blueprint version. Let the Research Lead continually improve the system through observed, versioned, testable development work, while preserving Director-held authority over research goals/resources and independent approval for protected control-plane changes. This captures the practical benefit of runtime learning without making the agent the sole author, evaluator, and approver of its own authority.