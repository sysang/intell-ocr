# System Design Guideline
## Autonomous Research Team for Applied AI: LLM & Agentic Systems

**Version:** 1.4 — Proposed Pi Subagents Architecture with Beads task management

> Filename note: promoted from draft `blueprint-draft-v1_0.md`; this file (`blueprint-v1.md`) is now the authoritative working file.

**Primary objective:** Build an autonomous, evidence-driven research system that turns a human-defined direction into a research roadmap, implemented experiments, evaluated findings, and a rigorous final report. The Research Lead host uses `pi-subagents` to call seven fixed children (the Research Advisor, Engineering Worker, three specialist architects, and two OKF knowledge services) and an on-demand pool of general subagents for bounded tasks outside the seven fixed roles' scopes.

---

## 1. System objectives and design principles

### 1.1 Mission

The research system operates as a small autonomous team with three core roles, named advisors and knowledge services, and an on-demand pool with no governance role (P1, §2.4, §3.5):

- **Research Lead:** The operational owner responsible for planning, investigating, implementing, experimenting, evaluating, analyzing, and reporting.
- **Research Advisor:** The intellectual and methodological reviewer responsible for theoretical guidance, problem clarification, critical assessment, and quality assurance.
- **Engineering Worker:** The bounded implementer responsible for writing code and tests to implement Lead-assigned functionality. It executes only explicitly assigned work packages and returns observed evidence; it owns no research decisions.

The human research director provides research directions, goals, constraints, and feedback when necessary.

The core research roles are defined in `.pi/agents/` alongside specialist consultants and knowledge services (full roster: §2.4), but they occupy different positions in Pi:

- **Research Lead** is the host/main Pi agent. Start the working session from the repository root with `pi --append-system-prompt .pi/agents/research-lead/agent.md`. It owns the research work and directly orchestrates Advisor consultations/reviews and Worker implementation assignments.
- **Research Advisor** is a Pi subagent definition, invoked by the Research Lead through the `pi-subagents` `subagent` mechanism.
- **Engineering Worker** is a Pi subagent definition, invoked by the Research Lead through the same `subagent` mechanism for bounded implementation work.

```text
Human research director
          |
          v
Main Pi session + Research Lead instructions
(pi --append-system-prompt .pi/agents/research-lead/agent.md)
          |
          +--> Research Lead plans / investigates / evaluates /
          |    analyzes / reports in the host session
          |
          +--> subagent({ agent: "research-advisor", task: ... })
          |          Consultation or independent artifact review
          |
          +<-- Structured advice / review findings
          |
          +--> subagent({ agent: "engineering-worker", task: ... })
          |          Bounded implementation work package
          |
          +<-- Structured result: files changed + observed test evidence
          |
          v
Research Lead verifies evidence, accepts or rejects work,
continues / revises / suspends / asks the human
```

The Research Lead orchestrates the lifecycle from the active host context; there is no separate Research Lead child run or checked-in lifecycle workflow script in the initial design. The Advisor and the Engineering Worker are the research-role subagents. Human involvement is reserved for decisions requiring human authority, unavailable information, changes to major research objectives, or unresolved critical issues; the host Research Lead asks the human directly when needed.

### 1.2 Core principles

**P1. Fixed roles, flexible task capacity.** The seven named children remain the fixed roster (§2.4); only their designated roles have standing responsibilities. Do not add a Planner, Critic, Reviewer, or Evaluator as a lifecycle role. The Lead considers operator-approved general subagents only for bounded tasks outside the scope of all seven fixed roles (§3.5). Pool members have no lifecycle authority and cannot replace a fixed role on work it covers. The Lead is the sole invoker of the pool and both OKF services.

**P2. One accountable owner.** The Lead owns every research deliverable. Advisor feedback does not transfer implementation responsibility.

**P3. Host-agent orchestration, dynamic dual-loop lifecycle.** The Research Lead host prompt defines a non-deterministic research cycle — PLANNING → IMPLEMENTATION → EVALUATION → ANALYSIS — with a bounded inner loop (IMPLEMENTATION ⇄ EVALUATION), a bounded outer loop (plan-cycle → ANALYSIS → revised plan-cycle), mandatory Advisor reviews at loop exits and gates, and explicit termination conditions. It uses `pi-subagents` to invoke the Advisor directly. These are role/prompt-level obligations, not application-enforced workflow gates; a separate Pi permission/policy extension would be needed for non-bypassable enforcement.

**P4. Evidence over agreement.** Advisor endorsement is not proof of correctness. Tests, source verification, experimental observations, and reproducibility determine whether claims are supportable.

**P5. Uncertainty-aware consultation.** The Lead assesses understanding and readiness before meaningful work. Unresolved uncertainty triggers Advisor consultation.

**P6. Mandatory independent review.** PLAN_GATE, INNER_EXIT_GATE, CYCLE_GATE, and REPORT_GATE each require an Advisor verdict, even when the Lead reports high confidence. Individual inner-loop iterations use per-attempt checks plus targeted consultation on triggers; they do not each require a gate review. Verdict/route/next-state combinations follow the authoritative table in §8.4.

**P7. High-information consultation.** Advisor interactions use focused questions, decision-oriented briefs, and references to primary evidence rather than complete conversation histories.

**P8. Research integrity.** Negative results, unresolved questions, failed experiments, and contradictory observations must be preserved and reported.

**P9. Durable execution via git checkpoints.** The Research Lead maintains project artifacts, decisions, and checkpoints in the research workspace so work can resume in a new or recovered host session — and checkpoints mean git commits, not unsaved working-tree state. Commit at every gate decision, cycle boundary, and accepted workspace-changing delivery, with messages naming the gate, verdict, and cycle (e.g. `CYCLE_GATE approve/replan cycle 2, manifest-v3`). Never rewrite published history; versioned artifacts plus manifest hashes make each commit independently auditable. Advisor subagent run/session records provide consultation traceability, but Pi runtime artifacts are not the long-term research source of truth and their retention is configuration-dependent.

**P10. Resource-aware autonomy with human-held stop authority.** Every research project operates within explicit budgets for computation, model usage, iteration, and external actions, tracked by the Lead in project state. Monitoring is the director's prerogative: the human research director watches expenditure with their own tools and alone decides to cease the research. On exhaustion of project-wide resource budgets (e.g., tokens, compute, spend), the Lead HOLDs, reports consumption honestly, and awaits the human decision. Assignment and loop limits have their own bounded recovery and stop rules (§8.4–§8.6, §8.9.3); none authorizes spending past a project-wide resource budget.

---

## 2. Architectural decomposition

The target has three role definitions and one host/subagents split:

1. **Research Lead host prompt:** `.pi/agents/research-lead/agent.md`, appended to the main Pi session at startup.
2. **Research Advisor subagent:** `.pi/agents/research-advisor/agent.md`, discovered and invoked through `pi-subagents`.
3. **Engineering Worker subagent:** `.pi/agents/engineering-worker/agent.md`, discovered and invoked through `pi-subagents` for bounded implementation work.

The Lead classifies each standalone task against the fixed roster before assigning it (§3.5). Work within a fixed role's scope goes to that role; only work outside all seven fixed scopes may be considered for the general pool. No separate workflow script or engine, new standing role, or second dispatch mechanism is needed.

### 2.1 Pi-native logical architecture

```text
HUMAN RESEARCH DIRECTOR
          |
          v
MAIN PI SESSION + RESEARCH LEAD HOST PROMPT
pi --append-system-prompt .pi/agents/research-lead/agent.md
          |
          +--> Lead investigates / plans / evaluates / reports;
          |    assigns bounded implementation packages to Worker
          |
          +--> Lead invokes `subagent` for Research Advisor
          |       fresh context + focused brief + artifact references
          |<-- structured advice or review verdict
          |
          +--> Lead invokes `subagent` for Engineering Worker
          |       scoped spec + file paths + acceptance criteria
          |<-- structured result: changes + observed test evidence
          |
          v
Lead records decisions, verifies evidence, and decides whether to
continue, revise, suspend, or ask the human
          |
          v
VERSIONED RESEARCH PROJECT WORKSPACE
```

The Research Lead is the host/main agent, not a child agent. It maintains the active lifecycle and owns deliverables. `pi-subagents` supplies the Advisor child session, model selection, run/session tracking, and child controls; it does not impose the research-stage state machine. The Research Lead's instructions and project records govern the research process.

### 2.2 Pi deliverables and startup

The initial target consists of the core role definitions, specialist consultants, and knowledge services under `.pi/agents/` (full roster: §2.4; incremental milestones: §13) and the existing Pi Subagents extension:

```text
.pi/
├── agents/
│   ├── research-lead/
│   │   └── agent.md       # host instructions; appended to main Pi context
│   ├── research-advisor/
│   │   └── agent.md       # Pi subagent definition with frontmatter + prompt
│   └── engineering-worker/
│       └── agent.md       # Pi subagent definition with frontmatter + prompt
│   ├── harness-architector/   # pre-existing specialist consultant (domain advice only)
│   ├── backend-architector/   # pre-existing specialist consultant (domain advice only)
│   ├── frontend-architector/  # pre-existing specialist consultant (domain advice only)
│   ├── okf-reader/            # knowledge service: read-only hub retrieval (Lead-invoked only)
│   └── okf-writer/            # knowledge service: bounded hub maintenance (Lead-invoked only)
└── settings.json         # optional agent-discovery exclusion for research-lead
```

Start Pi from the repository root:

```bash
pi --append-system-prompt .pi/agents/research-lead/agent.md
```

The main session must have `pi-subagents` loaded so the host Research Lead can call its `subagent` tool. The Research Lead file is loaded by the CLI prompt flag; it is not invoked as a child. The Advisor file is the child-agent definition. Because `pi-subagents` can recursively discover project agents, keep the Research Lead prompt out of the child catalog—use it as plain host prompt text and/or exclude `agents/research-lead` with `subagents.agentExcludeDirs` in `.pi/settings.json` if its format would otherwise be discoverable. The exclusion does not prevent `--append-system-prompt` from loading the file.

Per-project research records, code, experiments, reviews, decisions, and reports remain in a versioned research workspace as described in Section 7. These are project artifacts, not additional agent definitions or a workflow script.

### 2.3 Host-led orchestration and review enforcement

The Research Lead host prompt defines the loop discipline (inner/outer loop routing, cycle counters, termination conditions), readiness check, consultation triggers, mandatory loop-exit and gate reviews, and escalation policy. For a consultation or stage gate, the Lead launches `research-advisor` directly through `pi-subagents`, supplies a focused decision/review packet, and inspects the child result. The Advisor runs with fresh context and read-only access to the actual cited artifacts. The Lead records the advice/review, verifies required tests and evidence, and then continues or revises its own work.

Use a structured Advisor response contract and Pi structured output where appropriate; check the verdict and cited evidence rather than relying on free-form agreement. A valid schema or successful Advisor child run proves only response shape/run completion—not scientific correctness.

The host stays actively aware of every child run it launches — silent stalls are a first-class failure mode. After each dispatch the Lead confirms launch success promptly (status check against the recorded run ID), polls bounded background runs instead of assuming completion, and reconciles run/session artifacts on host resume. Record every child failure (launch rejection, mid-run error, timeout, missing or invalid result) with the error or validation findings, affected assignment or gate, and next action. For Worker and pool work, use the assignment ledger (§8.9); for other child calls, use the relevant project-state records. Apply dependency-scoped recovery and notification under §8.6; never retry beyond the applicable cap. Before any real research run, smoke-test the seven fixed child definitions (Advisor, Worker, three architects, reader, writer) with a trivial task. Verify pool candidates before every launch, including smoke tests (§10.2).

This design intentionally relies on the host Research Lead to follow the mandatory lifecycle. `pi-subagents` does not enforce research-stage gates on direct host actions. If non-bypassable policy enforcement becomes a requirement, add a separately designed and tested Pi permission/policy extension; do not claim the role prompts alone provide hard enforcement.

### 2.4 Agent separation

| Responsibility | Research Lead (host) | Research Advisor (subagent) | Engineering Worker (subagent) | Specialist architects (subagents) |
|---|---|---|---|---|
| Interpret research direction | Owns | Clarifies | — | — |
| Define research questions | Owns | Challenges | — | — |
| Literature review | Executes | Assesses relevance and coverage | — | — |
| Research methodology | Designs | Reviews and improves | — | Advises on harness / backend / frontend design questions |
| Research roadmap | Creates | Approves or requests revision | — | — |
| Implementation | Assigns, verifies, accepts | Reviews design and evidence | Executes assigned package only | Consulted by Lead or Worker on domain questions; writes nothing |
| Experiment execution | Assigns / runs, owns results | Challenges validity | Runs assigned commands, reports observed output | Advises on harness, scale, and performance design |
| Statistical analysis | Executes | Reviews interpretation | — | — |
| Final report | Writes | Critically reviews | — | — |
| Project status | Maintains | Reads as necessary | Reads assigned task context only | Reads as necessary |
| Research decisions | Proposes and implements | Advises and reviews | Makes none; reports blockers | Advises within domain; makes none |
| Human escalation | Asks the human directly when necessary | Can recommend escalation | Reports blocker to Lead (never contacts human directly) | Recommends via caller (never contacts human directly) |
| Budget management | Owns project-level budget decisions | Uses allocated consultation budget | Uses allocated implementation budget | Uses allocated consultation budget |

The three specialist advisors are pre-existing read-only roles the team consults for domain expertise, not research governance:

- `harness-architector` (`.pi/agents/harness-architector/agent.md`) — agent harnesses, skills, subagents, context/memory, workflows, governed adaptation.
- `backend-architector` (`.pi/agents/backend-architector/agent.md`) — architecture style, database/storage, APIs/messaging, security/auth, scalability/performance.
- `frontend-architector` (`.pi/agents/frontend-architector/agent.md`) — rendering, state management, build/performance, design systems, accessible components.

All three are caller-agnostic: the Lead consults them directly with decision-oriented briefs (same consultation discipline as Advisor Modes A/B, §6), and the Worker may consult them from inside a package through bounded nested delegation, recording every run ID and treating their output as unverified input until checked against the acceptance criteria. Two scopes govern this nested collaboration, and they behave differently. Capability scope (tools, context, delegation depth) narrows downward by design: each level sees only what its task requires (least privilege). Discovery scope (which agent definitions a run can see and launch) must instead remain sufficient: the three architects must stay resolvable from a Worker's nested position, or the consult step is dead on arrival and every expertise-dependent package stalls on BLOCKED. Sufficiency is proven by execution, not assumed from host-level discovery — the Worker→architect dry run must pass before any real research depends on the path. Specialist advice never authorizes actions and never substitutes for a gate verdict — only `research-advisor` reviews gates, and only the Lead accepts work. No edits to the specialists' own definitions are required.

Two knowledge services maintain the documentation system so the Lead orchestrates instead of clerking:

- `okf-reader` (`.pi/agents/okf-reader/agent.md`) — read-only retrieval from the hub bundle: minimum sufficient attributable evidence plus trust/freshness signals and explicit gaps, per its RESULT.md contract. Never judges, never writes, never delegates.
- `okf-writer` (`.pi/agents/okf-writer/agent.md`) — bounded maintenance of hub concept records, indexes, and logs as an OKF v0.2 bundle: frontmatter, cross-links, `validate_okf.py` bundle-check before publishing, `needs_review` (never silent improvisation) on conflict, contradiction, or unsafe publication. Never commits, never touches `src/` or project-state counters.

The Lead is their sole invoker and owns everything they produce until verified: reader gaps become investigation tasks, writer `needs_review`/`rejected` results become Lead triage, and even `committed` results get a Lead spot-check before gate reliance. Record-vs-artifact boundary: the writer curates concept records, indexes, and logs; execution artifacts (`src/`, experiment outputs, Worker plan files, manifests, `project-state.json`) are written directly by their producers and indexed — not rewritten — by the writer. Canonical format authority is the agent-local OKF v0.2 specification copies (`.pi/agents/okf-reader/spec/`, `.pi/agents/okf-writer/spec/`); the older v0.1 skill copy is background, not authority.

The **general subagent pool** is separate from the fixed roster. It reuses existing Pi subagent definitions for Lead-assigned tasks with permissions scoped to each assignment, including writes or execution when explicitly granted. See §3.5 for when to delegate, how to qualify a pool member, and what it may return.

The Advisor's subagent definition must have a strict read-only tool allowlist and no `write`, `edit`, or general-purpose shell access. The Worker's subagent definition must have a bounded write-capable allowlist (read/inspect tools plus `edit`, `write`, and scoped command execution for assigned paths and tests), the `implementation-workflow` and `problem-framing-and-autonomous-decision-making` skills, and a bounded nested-delegation grant (`allowNestedSubagents: true` capped by `maxSubagentDepth: 2`) so it can decompose major packages as the skill directs — never unrestricted fan-out, and never delegation to the Lead role. Direct Worker→Advisor consults are prohibited: they bypass the Lead's consultation plan and can never produce a gate verdict (verdicts are Lead-requested and manifest-bound only). Worker uncertainty goes to its skills, to nested architect consults, or back to the Lead as BLOCKED. The host Research Lead has the tools needed to run the research cycle and dispatch the fixed roster and general pool through `subagent`. Pi tool allowlists narrow Pi tools but do not themselves provide operating-system isolation.

---

## 3. Research Lead specification

### 3.1 Primary capabilities

The Lead requires competence in six areas.

**Research framing**

Convert an open-ended research direction into precise questions, hypotheses, experimental objectives, success criteria, and bounded work packages.

**Technical investigation**

Search, retrieve, compare, and synthesize scientific papers, technical documentation, repositories, benchmarks, and existing implementations.

**Software engineering**

Specify bounded implementation work packages (scope, target paths, acceptance criteria, verification commands), assign work within the Engineering Worker's remit to that role, and verify the returned evidence (§3.5). Only the Lead decides whether the implementation satisfies the methodology and accepts it into the project.

**Experimental methodology**

Construct baselines, identify confounding variables, design controls, run experiments, and collect measurements.

**Scientific analysis**

Interpret quantitative and qualitative findings, test alternative explanations, estimate uncertainty, and distinguish evidence from conjecture.

**Technical reporting**

Produce reproducible research reports connecting questions, methods, observations, results, conclusions, and limitations.

### 3.2 Mandatory task-readiness assessment

Before beginning each meaningful task, the Lead must execute a readiness check.

This should be a structured operation, not merely a system-prompt instruction to "be confident."

The check should answer:

| Dimension | Required assessment |
|---|---|
| Problem understanding | Can I express precisely what must be accomplished? |
| Information | Do I have the necessary facts, requirements, and evidence? |
| Methodology | Do I know a defensible method for completing the task? |
| Technical competence | Can I implement or execute that method? |
| Verification | Can I determine whether the result is correct? |
| Risk | What could invalidate the approach or conclusion? |
| Uncertainty | What important issues remain unresolved? |

Readiness is classified as:

- **READY:** The task, approach, and verification criteria are sufficiently clear.
- **INVESTIGATE:** A specific uncertainty can likely be resolved through bounded, low-cost information gathering.
- **CONSULT:** Meaningful uncertainty requires Advisor judgment.
- **BLOCKED:** Missing authority, resources, or essential information prevents responsible progress.

The Lead records the readiness classification and its evidence in the active task/project state. For `CONSULT`, the host directly invokes the Advisor subagent; there is no separate workflow component routing the request.

The Lead should not assign arbitrary numerical confidence scores as though they were calibrated probabilities.

Confidence must be tied to observable evidence.

For example:

> The algorithm and implementation approach are established, the benchmark and baseline are available, and the output can be verified by deterministic tests. No unresolved methodological concern currently prevents execution.

This is more useful than declaring "confidence: 95%."

### 3.3 Uncertainty classification

The Lead should distinguish different kinds of uncertainty.

| Type | Example | Preferred response |
|---|---|---|
| Factual | What does a paper actually establish? | Retrieve the primary source |
| Conceptual | Is this hypothesis theoretically plausible? | Consult Advisor |
| Methodological | Does this experiment isolate the variable of interest? | Consult Advisor |
| Technical | How should this library be used? | Inspect documentation and test |
| Interpretive | Do results support the causal claim? | Consult Advisor |
| Strategic | Which research direction has the highest value? | Consult Advisor; escalate material priority changes |
| Resource | Can this experiment fit the remaining budget? | Calculate and revise scope |

Not every uncertainty requires immediate consultation.

However, if the Lead cannot resolve a material uncertainty through clearly bounded investigation, consultation becomes mandatory.

### 3.4 Mandatory consultation triggers

Consult the Advisor when:

1. The research question cannot be precisely formulated.
2. Critical theoretical assumptions cannot be justified.
3. Multiple plausible methodologies have materially different implications.
4. The Lead cannot devise a credible evaluation method.
5. Important evidence is contradictory.
6. Unexpected results undermine the original research hypothesis.
7. Repeated implementation failures suggest a conceptual design problem.
8. A conclusion requires substantial interpretation beyond the observations.
9. A research scope change could invalidate earlier decisions.
10. The system reaches a required stage-review gate.

A critical principle:

**Do not use self-reported confidence to bypass a mandatory review or an objective high-risk trigger.**

For Pi orchestration, a material consultation trigger leads the host Research Lead to construct a focused consultation package and launch `research-advisor` directly via `subagent`. The Lead reviews the returned advice, records the decision and evidence references, and continues or revises its own work. If the Lead is blocked, it pauses and asks the human rather than converting the blocker into an implicit approval.

### 3.5 Delegate concrete, self-contained work

**Delegation is mandatory for a meaningful `READY` task that is easy to hand off, has concrete scope, and has a suitable authorized subagent within budget.** The Lead first looks for independently verifiable pieces rather than keeping a whole mixed task in the host. A handoff is ready when it can name the deliverable, permitted inputs and actions, exclusions, and a checkable acceptance criterion without sharing the Lead's live reasoning. Domain fit, independent checking, or useful parallelism can improve the result; the Lead does not have to prove improvement in advance. Stage descriptions that say the Lead executes work describe its accountability, not a requirement to do every step personally.

- **Classify against the fixed roster first.** Compare the task's deliverable with the seven fixed-role scopes (§2.4). Split mixed work into separable packages when practical; bundling tasks never makes in-scope work eligible for the pool. If a fixed role covers the task, route it to that role: for example, the Engineering Worker handles an assigned test fixture, the Advisor handles a gate review, and `okf-reader` retrieves hub evidence. Only if none of the seven roles covers the task may the Lead consider the general pool, for example to extract findings from a supplied set of primary papers. Record why no fixed role covers it before dispatch. A matching agent being busy or unavailable, or a pool member being cheaper or more capable, does not make the task eligible for the pool. The Lead retains research judgment, routing, acceptance, and director communication. It may do tightly coupled work or trivial actions directly; for a meaningful task not delegated, record the concrete reason in its existing readiness/assignment record. If no eligible child can take it, the Lead may proceed directly only where existing budget, HOLD, and authority rules allow it; required calls have no pool or host substitute.
- **Use an approved pool, not the entire discovered catalog.** The operator supplies the Lead with explicit approvals for canonical names bound to a resolved profile and its effective capabilities (§10.2). The Lead chooses among verified approvals without asking again for each assignment. A pool member may use only capabilities permitted by both its approved profile and the assignment. Name permitted read inputs separately from any writable paths, authorized commands or tool operations, and external actions; read-only does not imply unrestricted read access. Pool members cannot change governance records or state counters, commit, delegate, issue gate verdicts, make research decisions, accept work, or contact the director. No agent is created ad hoc.
- **Track tasks in Beads and execution in the project ledger.** Use [§8.9](#89-assignment-ledger-and-delegation-lifecycle) for the task link, issued brief, dispatch, result, and Lead acceptance. No pool result can satisfy a required fixed-role call, even if it contains a verdict or other review-like output. Handle failures by dependency under §8.6.
- **Use `codemode` where it helps.** The Lead and approved pool members may use it to batch or filter authorized tool calls or run explicitly permitted non-LLM models, such as classifiers. Pi's `codemode` runs scripts in a locked-down QuickJS WebAssembly sandbox, with no direct Node APIs, filesystem, network, or timers. Scripts reach the outside world through the session's tools and model APIs. Those calls can have real side effects and are not rolled back on script failure. The sandbox constrains the script, not the permissions of the tools or models it calls; the same assignment limits apply to direct and scripted calls (§10.6).

---

## 4. Research Advisor specification

### 4.1 Advisor mission

The Advisor should behave like a rigorous principal research scientist or research director.

Its primary responsibility is to improve the epistemic quality of the research.

The Advisor must optimize for:

- Theoretical correctness.
- Methodological rigor.
- Explanatory power.
- Plausibility of hypotheses.
- Scientific validity.
- Identification of hidden assumptions.
- Recognition of alternative explanations.
- Reliability of conclusions.
- Efficient allocation of research effort.

The Advisor is not primarily a conversational assistant or motivational collaborator.

### 4.2 Three consultation modes

**Mode A — Problem solving**

Used when the Lead is uncertain how to proceed.

The Advisor should diagnose the problem, identify the conceptual obstacles, propose alternative approaches, compare their merits, and recommend a defensible next action.

**Mode B — Design review**

Used when the Lead has proposed a research or technical design.

The Advisor should examine assumptions, requirements, alternatives, failure modes, missing controls, and acceptance criteria.

**Mode C — Critical artifact review**

Used at mandatory research stage gates.

The Advisor must evaluate the submitted artifact against an explicit rubric and provide an actionable review decision.

### 4.3 Critical review behavior

The Advisor must actively look for:

- Invalid assumptions.
- Unsupported generalizations.
- Incorrect interpretation of scientific sources.
- Confounding variables.
- Weak or inappropriate baselines.
- Implementation defects.
- Data leakage.
- Measurement bias.
- Statistical weaknesses.
- Contradictions between evidence and conclusions.
- Missing limitations.
- Research questions that remain unanswered.

Agreement should follow evaluation, not precede it.

The Advisor should explain not only what is wrong, but why it matters and what evidence or correction would resolve the issue.

### 4.4 Advisor decision contract

Every mandatory gate review must return a structured decision bound to the exact submission it assesses.

```json
{
  "gate": "PLAN_GATE | INNER_EXIT_GATE | CYCLE_GATE | REPORT_GATE",
  "review_target": "artifact-manifest-id@version (what was actually inspected)",
  "verdict": "approve | revise | block | inconclusive",
  "summary": "Concise overall assessment",
  "findings": [
    {
      "severity": "critical | major | minor",
      "issue": "Clearly identified problem",
      "justification": "Why this is a problem",
      "evidence_refs": ["artifact-or-source-id"],
      "required_action": "Specific correction or verification"
    }
  ],
  "alternative_explanations": [],
  "residual_uncertainties": [],
  "recommended_next_actions": [],
  "additional_evidence_required": []
}
```

**Verdict meanings (assessment of the submission, not a routing order).**

- **Approve** means the submission passes the gate rubric — not that its claims are proven.
- **Revise** means corrections are required before the gate passes; the response must state them as `required_action` items.
- **Block** means a fundamental methodological, safety, or validity problem was found; the response must say what would need to change for the work to continue responsibly.
- **Inconclusive** means the Advisor lacks sufficient evidence to determine pass/fail; the response must name the missing evidence in `additional_evidence_required`.

**Verdicts do not route by themselves.** The Lead selects the route using the authoritative table in §8.4. `approve` enables only the forward routes whose other conditions are met; `revise` normally permits bounded remediation (default max 2 revise rounds, then HOLD and escalate), subject to the CYCLE_GATE stop rules. `inconclusive` permits bounded evidence gathering plus one re-review, then HOLD if unresolved; `block` requires HOLD triage and converts to SUSPENDED only on a confirmed-unresolvable blocker or human decision.

**Fail-closed validation.** The Lead must validate every gate response before acting on it: parseable against the schema above, `gate` matching the gate actually invoked, and `review_target` matching the submitted manifest version. For PLAN_GATE, the request identifies the phase (`protocol` or `readiness`), and the submitted manifest must match that phase; a protocol verdict cannot be reused for readiness. Any failure — malformed output, missing verdict, wrong gate, wrong phase target, stale manifest — is a no-verdict: the Lead records it and HOLDs the gate during bounded re-requests (default max 2); escalate if recovery is exhausted or the Advisor is confirmed unavailable. The same fail-closed rule covers knowledge-service results at gates (§8.7) and mechanical tool results (§10.7): no gate advances on an unvalidated or stale required result or a failed/missing required check. Silence, an expired run, or a `complete` run status is never approval. A verdict is bound to the reviewed manifest; changes to its covered evidence require a fresh verdict before relying on the changed package, except for the explicit readiness coverage rule in §5.3.

**Bounded evidence expansion.** When the Advisor requests more evidence, the Lead supplies it in at most 2 expansion rounds per gate. A follow-up review — whether it resumes context or starts a fresh child — must carry the original rubric, the prior findings, and the same manifest version (or a new versioned manifest if evidence changed). Advisory consultations and mandatory gate verdicts are labeled differently in project records; advice never satisfies a gate unless the call explicitly applied the gate rubric to the submitted manifest.

For Pi, return this contract as schema-constrained structured output when configured, otherwise as the specified JSON response. This gate is instruction-level, not runtime enforcement; a separate Pi permission/policy extension would be required to make bypass impossible.

### 4.5 Preventing superficial peer review

A serious problem arises when the Advisor sees only the Lead's interpretation of its own work.

For critical reviews, the Advisor should be able to inspect:

- The actual research specification.
- Original scientific sources.
- Code changes and relevant source files.
- Test results.
- Raw or sampled experimental observations.
- Evaluation scripts.
- Statistical summaries.
- Claim-to-evidence mappings.

The Advisor can initially receive a compact summary, but must be able to request specific primary artifacts.

For high-risk reviews, a useful procedure is:

1. Present the research question, rubric, and relevant primary evidence.
2. Ask the Advisor for an independent assessment.
3. Present the Lead's interpretation and self-review.
4. Ask the Advisor to identify disagreements, missing evidence, and potential errors.

This reduces the risk of anchoring on the Lead's conclusions.

It does not eliminate correlated model failures, so independent tests and human escalation remain necessary.

---

## 5. Research workflow design

### 5.1 Research lifecycle — dynamic dual-loop (non-deterministic)

The research workflow is non-deterministic: the path through PLANNING, IMPLEMENTATION, EVALUATION, and ANALYSIS is decided at runtime from evidence, Advisor verdicts, loop counters, and the termination conditions. REPORTING is entered only through the CYCLE_GATE `report` route; it is not a stage the Lead can advance to unilaterally. Gate names are canonical — PLAN_GATE, INNER_EXIT_GATE, CYCLE_GATE, REPORT_GATE — and the authoritative verdict/route/next-state table is §8.4; if any other section appears to disagree with it, §8.4 governs. The Research Lead host agent owns all routing decisions. It delegates consultation and independent review to the `research-advisor` Pi subagent through the `subagent` tool; it is not launched as a subagent itself.

```text
Human request
     |
     v
Research Lead host session
     |
  PLANNING ----------> PLAN_GATE (protocol approval)
     |
     v
  +---------------- OUTER CYCLE n (plan v_n) ----------------+
  |  1. IMPLEMENTATION ⇄ EVALUATION   (inner loop)          |
  |     PLAN_GATE readiness before full evaluation          |
  |     |
  |     v                                                    |
  |  2. INNER_EXIT_GATE (Advisor review of evidence package,|
  |     complete or explicitly incomplete-for-diagnosis)    |
  |     |
  |     v                                                    |
  |  3. ANALYSIS + CYCLE_GATE (Advisor-reviewed limitation  |
  |     diagnosis, progress verdict, and route)             |
  |     |
  |     +-- objective achieved ---> REPORTING               |
  |     +-- approved replan + budget remains ---> cycle n+1 |
  |     +-- HOLD or terminal stop per §8.4 ---------------->|
  +----------------------------------------------------------+
```

Two deliberately different pauses: **HOLD** is resumable (awaiting evidence, a bounded re-review, Worker rework, or a human decision); **SUSPENDED** is terminal and always produces a preserved-evidence status report — distinct from an approved final research report, which only COMPLETED produces.

**Two PLAN_GATE phases, plus checks and exit review.** Protocol approval comes before substantial implementation. A separate readiness approval of the built baseline and passed tests is required before the first full evaluation of each cycle (§5.3). Per-attempt checks (tests and smoke evaluations) run after implementation changes; they never supply an Advisor verdict. Later fixes stay covered by readiness approval only under §5.3. *INNER_EXIT_GATE* is the mandatory Advisor review that closes the inner loop. It admits two package kinds: a complete evidence package, or an explicitly incomplete/invalid package submitted **for diagnosis only** (attempt budget spent, or the fix would require a plan change). A diagnosis-only package may route to ANALYSIS; it may never support a success claim or a `report` route.

**Inner loop — IMPLEMENTATION ⇄ EVALUATION.** Commits endeavor to achieve the best outcome under the current approved plan (plan v_n): build/fix, run smoke tests and evaluations, diagnose failures, and iterate. The Lead retains tightly coupled, plan-sensitive work and routes standalone packages by scope (§3.5): implementation within the Engineering Worker's remit goes to that role; only work outside all fixed roles' scopes is eligible for the pool. The Lead applies the readiness, dispatch, and acceptance contract in §8.9. The loop stays inside the plan; it does not change research questions, hypotheses, metrics, or validity criteria. A fix that requires changing the plan (new hypothesis, different baselines/metrics, relaxed success criteria) exits early to ANALYSIS with the evidence marked incomplete-for-diagnosis, instead of silently redefining success inside the loop.

**Outer loop — [PLANNING → IMPLEMENTATION → EVALUATION] → ANALYSIS → [PLANNING → IMPLEMENTATION → EVALUATION].** Commits endeavor to improve or resolve limitations of the initial plan: each outer cycle (n = 1, 2, …) runs the current plan through implementation and evaluation, then ANALYSIS diagnoses what limited the outcome (method, baselines, data, metrics, scope, assumptions) and proposes plan v_{n+1}. Only an Advisor `approve` at CYCLE_GATE on a cycle decision proposing `replan`, with the conditions in §8.4 met, authorizes the Lead to start and charge the next cycle. Drafting a replacement plan is not authorization.

**Termination conditions (checked at every ANALYSIS gate, and immediately when discovered):**

1. **Objective achieved** — the approved success criteria are met with valid evidence and Advisor concurrence → enter REPORTING, then COMPLETED.
2. **Unsolvable blocker** — a fundamental methodological, safety, resource, or validity problem with no responsible workaround (Advisor `block` verdict the Lead cannot remediate, missing authority/data, invalidated core assumption) → HOLD immediately for triage (preserve evidence, ask the human where human authority could unblock); convert to SUSPENDED with an honest status report only when confirmed unresolvable or the human so decides. Never downgrade a blocker into an implicit success.
3. **Stagnation despite committed effort** — significant effort has been committed without noticeable positive progress. Quantification: a per-project outer-cycle budget of **3 to 5 outer cycles** (default 4, set in the research charter; the human may override within [3, 5]). Each ANALYSIS records a progress verdict (`advanced | marginal | stalled | regressed`) with evidence. Validated objective achievement can route to REPORTING even on the final allowed cycle. The cap prohibits authorizing cycle N+1 even when progress is `advanced`. Early stop: 2 consecutive `stalled`/`regressed` cycles with no credible new lever (charter-adjustable, default 2) also prohibits a new cycle. Apply §8.4 to decide whether the current cycle needs bounded remediation or HOLD, or can stop in SUSPENDED with a status report. Never start extra cycles to manufacture a positive result.

Before each meaningful task, the Lead assesses readiness. It investigates bounded factual/technical uncertainty directly, invokes the Advisor for material conceptual or methodological uncertainty, and asks the human when authority or essential information is missing.

```text
Lead task-readiness check
    |
    +-- READY ------> execute and verify
    +-- INVESTIGATE -> bounded investigation -> reassess
    +-- CONSULT ----> subagent(research-advisor) -> integrate advice
    +-- BLOCKED ----> pause and ask the human / report blocker

Inner-loop iteration complete (tests + evaluation run)
    |
    +-- executable checks pass, target met or attempt budget spent
    |       -> INNER_EXIT_GATE, then ANALYSIS only on approval
    +-- fix stays within plan v_n -> next IMPLEMENTATION iteration
    +-- fix requires plan change -> diagnosis-only INNER_EXIT_GATE
            (no silent redefinition)

ANALYSIS + CYCLE_GATE review (Advisor: interpretation + limitation
    diagnosis + progress verdict + route; see §8.4 table)
    |
    +-- approve + objective met -> REPORTING (REPORT_GATE)
    +-- approve/replan + no stop condition -> charge cycle n+1
    |       -> PLANNING -> PLAN_GATE (protocol for v_n+1)
    +-- revise -> bounded remediation and CYCLE_GATE re-review,
    |       or stop if the fix requires a new cycle and none is allowed
    +-- inconclusive -> bounded evidence + re-review, then HOLD if unresolved
    +-- block / no-verdict -> HOLD; no advancement
    +-- other terminal stop -> SUSPENDED + status report (see §8.4)
```

**Loop accounting (mandatory project state).** Track `outer_cycle`, `inner_attempt`, per-cycle progress, Advisor verdicts, and the remaining budget. Cycle 1 is charged at the start of initial planning; subsequent cycles are charged only on `CYCLE_GATE approve/replan`. A failed PLAN_GATE does not refund a charged cycle. Charge an inner attempt when implementation changes are integrated into the cycle workspace, even if evaluation never completes; log no-change interruptions without charging. Review rounds and consultation retries have separate counters; implementing a correction still follows the normal inner-attempt rule. Track all limits in `project-state.json` (§8.4–§8.5).

The Lead's host prompt and durable project records preserve lifecycle state across turns. `pi-subagents` manages Advisor and Worker child runs; it does not advance the research stage on the Lead's behalf or enforce the gate in application code.

### 5.2 Stage 1 — Research planning

**Objective:** Transform the user's research direction into an executable, falsifiable research program.

The Lead should:

1. Interpret the research goal.
2. Identify relevant concepts and prior work.
3. Build a targeted literature map.
4. Separate established findings from open questions.
5. Define specific research questions.
6. Formulate competing hypotheses.
7. Determine the minimum useful research scope.
8. Select research methods.
9. Identify relevant benchmarks, baselines, and datasets.
10. Define evaluation metrics and validity checks.
11. Estimate resources and research risks.
12. Produce a staged roadmap.

**Required artifacts**

- `research-charter.md`
- `literature-review.md`
- `hypotheses.md`
- `methodology.md`
- `evaluation-plan.md`
- `roadmap.md`

**Advisor review questions**

- Is the research question sufficiently precise?
- Are the hypotheses plausible and falsifiable?
- Does the proposed method actually test the hypotheses?
- Are major alternative explanations considered?
- Are important prior results missing?
- Can the proposed evidence support the intended claims?
- Is the scope efficient relative to the research objective?

**Gate (PLAN_GATE protocol):** The Advisor must approve the plan and evaluation protocol manifest for the authorized cycle before substantial implementation begins. This does not approve the eventual implementation baseline.

Where practical, record the experiment protocol before observing the primary evaluation results. Later exploratory modifications must be distinguishable from preregistered tests.

### 5.3 Stage 2 — Implementation

**Objective:** Build the software and experimental infrastructure required by the approved methodology.

The Lead decomposes the approved methodology into bounded work packages. Route each under §3.5, use [§8.9](#89-assignment-ledger-and-delegation-lifecycle) for the work package and its acceptance, and apply the role permissions in §10.6.

The Lead should decompose the stage into packages that together cover:
1. Inspection of existing code, libraries, and datasets.
2. Build or adapt experiment components.
3. Implement reference baselines.
4. Implement the proposed experimental treatments.
5. Write unit and integration tests.
6. Validate schemas and dataset preparation.
7. Configure model inference.
8. Create reproducible execution commands.
9. Run small-scale smoke tests.
10. Prepare the experiment for full evaluation.

**Required artifacts**

- Version-controlled source code.
- Dependency lockfiles and environment configuration.
- Dataset manifests and hashes.
- Baseline implementations.
- Experiment configuration files.
- Automated tests.
- Reproduction instructions.
- Implementation notes.

**Advisor review questions**

- Does the implementation conform to the research methodology?
- Are experimental conditions isolated correctly?
- Are the baselines valid?
- Is the test harness measuring the intended quantities?
- Are there sources of leakage or contamination?
- Can another researcher reproduce the execution?
- Are observed test failures understood?

**Gate (PLAN_GATE readiness):** Before the first full evaluation of each cycle, submit a separate versioned manifest containing the built baseline, the approved protocol reference, and observed passing results for the required tests. The Advisor must approve that readiness submission. Tests and smoke runs used to establish readiness may run before approval; full evaluation may not.

For a later fix within the approved protocol, the Lead may reuse readiness approval only if it records the exact revision and diff, passing per-attempt checks, and evidence that the interfaces, contracts, and validity assumptions the approval relied on are unchanged. Otherwise, including when coverage is uncertain, require a new readiness verdict before full evaluation. If the fix needs a protocol change, do not use readiness review to approve it: route through the diagnosis-only inner exit and CYCLE_GATE (§8.4).

Implementation approval does not establish that the scientific hypothesis is correct.

### 5.4 Stage 3 — Evaluation (empirical evidence)

**Objective:** Generate reproducible empirical evidence under the frozen protocol. Interpretation, limitation diagnosis, and the continue/replan/report routing decision belong to Stage 4 (ANALYSIS), not to this stage.

The Lead should:

1. Freeze or version the experimental protocol.
2. Execute the approved baselines.
3. Execute experimental treatments.
4. Collect raw outputs and execution metadata.
5. Repeat stochastic evaluations where appropriate.
6. Validate result integrity.
7. Calculate predefined metrics.
8. Analyze uncertainty and effect sizes.
9. Investigate failures and outliers.
10. Execute approved ablations and robustness checks.
11. Document deviations and exploratory findings.

This stage is the EVALUATION half of the inner loop: failed or weak results route back to IMPLEMENTATION for another iteration within the same plan (see 5.1), provided the fix does not change the plan. Differences from the previous inner attempt (what changed, what improved, what did not) are recorded per attempt so ANALYSIS can judge progress.

**Required artifacts**

- Immutable experiment configuration snapshots.
- Raw evaluation results.
- Experiment and inference metadata.
- Statistical analysis scripts.
- Metrics and figures.
- Ablation results.
- Failure taxonomy.
- Per-attempt evaluation notes (attempt id, code/config version, delta vs. previous attempt).

**Advisor review questions (inner-loop exit check)**

- Were the evaluation protocols followed?
- Are the measurements valid?
- Are the comparisons fair?
- Are the statistical methods appropriate?
- Are observed differences practically meaningful?
- Have negative results been preserved?
- Is the evidence package complete enough for ANALYSIS, or is another inner-loop iteration warranted?

**Gate (INNER_EXIT_GATE):** The evidence package must be complete and its integrity accepted (tests pass, provenance recorded) — or explicitly marked incomplete-for-diagnosis — before ANALYSIS. Corrective implementation work routes back through the inner loop; plan changes are forbidden here — they require the CYCLE_GATE `replan` route (see §8.4).

Do not modify a held-out evaluation set simply to obtain stronger results. Material protocol changes require a new experiment version and corresponding disclosure.

### 5.5 Stage 4 — Analysis (limitation diagnosis and cycle decision)

**Objective:** Interpret the evaluated evidence, diagnose what limits the current plan, and make the explicit routing decision: report (objective achieved), stop via HOLD/SUSPENDED (blocker/stagnation), or re-plan the next outer cycle. This stage is the hinge of the outer loop.

The Lead should:

1. Compare observations with the hypotheses and competing explanations.
2. Assess which claims the evidence supports, qualifies, or rejects.
3. Diagnose the binding limitation of plan v_n (method, baselines, data, metrics, scope, assumptions, budget).
4. Judge progress for this outer cycle: `advanced | marginal | stalled | regressed`, with evidence (metric deltas, resolved vs. open limitations, Advisor findings).
5. Propose the cycle decision, including plan v_{n+1} changes if proposing `replan` (hypothesis/method/metric/scope deltas and why they should break the limitation). Charter-level objectives and success criteria are out of scope for re-planning: changing them requires explicit human authorization, not a CYCLE_GATE verdict.
6. Apply the §8.4 transition table to the validated CYCLE_GATE verdict and termination predicates. At the cycle cap or early-stagnation stop, no next cycle may be authorized; use the verdict-specific rules for reporting, current-cycle remediation, HOLD, or SUSPENDED.
7. Record the decision, rationale, and evidence in `cycle-decision.json` before acting on it.

**Required artifacts**

- Evidence-to-hypothesis assessment.
- Threats-to-validity analysis.
- Limitation diagnosis for plan v_n.
- Progress verdict with supporting evidence.
- `cycle-decision.json` (decision ID, proposed route and selected §8.4 route when resolved, verdict/manifest refs, rationale, evidence refs, and any next-plan deltas). An unapproved `replan` proposal is not a charge record.

**Advisor review questions**

- Do the findings actually support the stated conclusions, or do they exceed the evidence?
- Could the effects be explained by confounding variables or alternative mechanisms?
- Is the diagnosed limitation actually the binding one, or a symptom?
- Would the proposed plan v_{n+1} plausibly resolve it, or just relabel it?
- Is the progress verdict honest given the metric deltas?
- Has a termination condition fired (objective achieved / unsolvable blocker / stagnation)?

**Gate:** No new outer cycle starts and no REPORTING begins without a valid `approve` at CYCLE_GATE covering the recorded decision and its evidence, subject to §8.4. The Advisor may request a draft next plan during remediation; record it with the current cycle and return it to CYCLE_GATE for review. Only `approve/replan` authorizes and charges cycle n+1. Then PLAN_GATE reviews that cycle's protocol before substantial implementation resumes.

### 5.6 Stage 5 — Reporting

**Objective:** Produce a rigorous technical report whose claims can be traced to evidence.

The Lead should prepare a report containing:

1. Executive summary.
2. Research problem and motivation.
3. Research questions.
4. Relevant literature.
5. Hypotheses.
6. Methodology and experimental design.
7. Implementation.
8. Evaluation protocol.
9. Results.
10. Interpretation and discussion.
11. Alternative explanations.
12. Limitations and threats to validity.
13. Conclusions and confidence boundaries.
14. Practical engineering implications.
15. Reproduction instructions.
16. Recommended follow-up research.

**Required artifacts**

- `research-report.md`
- `claim-evidence-matrix.md`
- Reproduction instructions.
- References and bibliography.
- Final artifact manifest.

**Advisor review questions**

- Are all important factual claims supported?
- Do interpretations exceed what the results establish?
- Are contradictory findings acknowledged?
- Is uncertainty represented appropriately?
- Is the report reproducible?
- Does the report answer the original research questions?
- Are recommendations proportionate to the evidence?

**Gate:** Final approval requires resolution of all critical review findings and independent verification of mandatory artifacts.

---

## 6. Advisor consultation and context engineering

This is one of the most important parts of the system.

The Lead must be an effective consumer of Advisor intelligence.

### 6.1 The consultation objective

An Advisor interaction should aim to maximize:

**Expected improvement in research decisions per unit of consultation cost.**

The goal is not minimizing tokens at all costs.

Omitting essential evidence may reduce token usage while substantially increasing the probability of a poor decision.

Instead, minimize redundant information while preserving what is necessary for the Advisor to reason correctly.

### 6.2 The consultation package

Every consultation should have a structured information package.

```yaml
consultation:
  id: CONSULT-001
  type: methodological_review

  research_context:
    goal: "Research question or objective"
    relevant_stage: planning
    current_task: TASK-004

  decision_required:
    question: "One precise question"
    impact: "Why this decision matters"

  established_facts:
    - claim: "Verified fact"
      evidence_ref: "SOURCE-001"

  current_approach:
    summary: "Proposed solution"
    rationale: "Why it was selected"

  uncertainty:
    description: "What is not understood"
    alternative_hypotheses: []
    known_failure_modes: []

  available_evidence:
    - artifact_ref: "ARTIFACT-123"
      relevant_section: "Section 3"

  constraints:
    remaining_budget: "Budget reference"
    implementation_limitations: []

  requested_output:
    - "Evaluate methodological soundness"
    - "Identify critical assumptions"
    - "Recommend an action"
```

The package should communicate enough information for a meaningful decision without reproducing the entire research history.

In the Pi implementation, the Lead prepares this package as a focused subagent task (or a small versioned artifact plus references) and launches `research-advisor` with fresh context. The Advisor returns structured advice/review findings; Pi records the child run and the Lead writes the durable decision/review record in the project workspace. Do not put private credentials or large raw datasets in the subagent task.

### 6.3 Information prioritization

Include information in this order:

1. The question or decision required.
2. Why it matters to the research objective.
3. The most relevant verified facts.
4. The Lead's current approach.
5. The uncertainty or disagreement.
6. Critical evidence and artifact references.
7. Resource or implementation constraints.
8. The requested form of Advisor response.

Do not automatically include:

- Entire agent conversations.
- Unrelated literature.
- Full execution logs.
- Large source files.
- Previously resolved decisions.
- Verbose narration of ordinary implementation steps.

### 6.4 Progressive evidence disclosure

Use a two-level consultation protocol.

**Level 1 — Decision brief**

Provide a focused summary and a small set of critical evidence references.

An initial budget of approximately 1,000–2,500 input tokens is a reasonable engineering starting point, not a proven optimum.

**Level 2 — Evidence expansion**

The Advisor may request exact source passages, code sections, experimental records, or additional observations.

This avoids paying to transmit large amounts of potentially irrelevant context while retaining the ability to investigate difficult problems deeply. Expansion is bounded per §4.4 (default max 2 rounds per gate, carrying the original rubric and prior findings); exceeding it HOLDs the gate rather than expanding indefinitely.

**Important:** An arbitrary compression target must never override evidence sufficiency.

### 6.5 Consultation quality checks

Before calling the Advisor, the Lead should verify:

- Is the question specific?
- Is there an identifiable decision to be made?
- Are the necessary assumptions explicit?
- Are facts separated from hypotheses?
- Are source references available?
- Are the relevant alternatives included?
- Is the expected output actionable?
- Would missing information materially distort the advice?

If the answers are unsatisfactory, improve the consultation package before sending it.

### 6.6 Example: poor versus effective consultation

**Poor consultation**

> I am researching prompting and LLM intelligence. Please think deeply and tell me how to design a good experiment.

**Effective consultation**

> Research question: Does semantically equivalent prompt variation produce measurable changes in frontier reasoning-model accuracy?
>
> Proposed experiment: Compare 20 verified paraphrases for each of 100 mathematical reasoning problems, across three models.
>
> Primary concern: Differences may be confounded by sampling variability, prompt-specific answer formatting, and changes in reasoning-token consumption.
>
> Relevant evidence: A prompt-sensitivity study reports evaluation artifacts related to answer matching. The experimental plan currently uses an exact-match grader.
>
> Please identify the critical threats to internal validity, propose the minimum necessary controls, and specify what evidence would justify a causal interpretation.

The second request makes far better use of an expensive Advisor model.

### 6.7 Preventing consultation overload

The system should implement:

- Separate budgets for mandatory reviews and exploratory consultations.
- Per-call token and inference limits.
- Maximum consultation attempts for the same unresolved issue.
- Reuse of prior Advisor decisions.
- Consultation caching for unchanged evidence and questions.
- Explicit invalidation when assumptions or artifacts change.
- Tracking of advice adopted, rejected, and empirically validated.

Before consulting, search the decision record to determine whether the same question has already been answered under equivalent conditions.

### 6.8 Advisor consultation should not become a bottleneck

Use a simple consultation-priority policy.

**Mandatory:** All stage reviews and critical methodological uncertainties.

**High priority:** Decisions with substantial expected impact on validity, implementation direction, or research cost.

**Normal priority:** Problems where Advisor knowledge is likely to reduce significant trial and error.

**Low priority:** Routine technical questions answerable through documentation, tests, or established decisions.

Mandatory reviews are never skipped for budget optimization.

If budget is exhausted, HOLD or narrow the research scope rather than silently removing required review.

---

## 7. Research artifacts, knowledge, and memory

### 7.1 Artifacts as the source of truth

Agent chat histories should not be the primary record of research.

Instead, use versioned artifacts.

Each research project should have a stable identifier, persistent tasks, source records, experiment runs, decisions, reviews, and final deliverables.

### 7.2 Suggested Pi and project structure

Keep the three role definitions separate from per-project research evidence:

```text
repository/
├── .pi/
│   ├── agents/
│   │   ├── engineering-worker/
│   │   │   └── agent.md       # discovered Pi subagent
│   │   ├── research-advisor/
│   │   │   └── agent.md       # discovered Pi subagent
│   │   ├── harness-architector/   # discovered specialist (read-only domain consultant)
│   │   ├── backend-architector/   # discovered specialist (read-only domain consultant)
│   │   ├── frontend-architector/  # discovered specialist (read-only domain consultant)
│   │   ├── okf-reader/            # knowledge service: read-only hub retrieval (Lead-invoked only)
│   │   ├── okf-writer/            # knowledge service: bounded hub maintenance (Lead-invoked only)
│   │   └── research-lead/
│   │       └── agent.md       # appended to the main Pi session
│   ├── extensions/beads-tools/  # planned Lead-only, typed Beads task tools (§8.9.2)
│   ├── plans/               # Worker plan files (implementation-workflow); written only when the package explicitly grants its own plan file — local scratch, not governance records
│   └── settings.json          # agent discovery + model overrides
└── research-projects/<project-id>/
    ├── change-and-progress-logs/   # CENTRAL GOVERNANCE HUB — the single authoritative record of how the project evolves; every gate decision, cycle transition, charter or planning change, review verdict, and progress checkpoint lands here (or is indexed here) before it counts as project truth. Maintained as an OKF v0.2 bundle: concept records, indexes, and logs via `okf-writer`; retrieval via `okf-reader`; state counters by the Lead
    │   ├── index.md                # master index table governing the whole hub: every entry (charter version, plan version, review verdict, decision, cycle) is a row pointing at its artifact; the retrieval map for audits, resumption, and REPORT_GATE confirmation
    │   ├── director-brief.md        # standing executive summary for the human director, refreshed every cycle: objective status, progress, spend-vs-budget, blockers, pending director decisions
    │   ├── charter/
    │   │   ├── research-charter.md
    │   │   └── scope-and-constraints.md
    │   ├── planning/
    │   │   ├── hypotheses.md
    │   │   ├── methodology.md
    │   │   ├── evaluation-plan.md
    │   │   └── roadmap.md
    │   ├── reviews/{planning,src,evaluation,analysis,reporting}/
    │   └── decisions/{decision-log.md,cycle-decision.json}
    ├── literature/
    │   ├── sources.jsonl
    │   ├── literature-review.md
    │   └── evidence-notes/
    ├── src/                            # ALL implementation lives under this tree and nowhere else: every executable artifact (methods, tests, evals, experiments, configs) is created, run, and versioned here
    │   ├── methods/                  # research implementations under study (candidate approaches, baselines under test)
    │   ├── tests/                    # unit and integration tests for methods and harnesses; per-attempt checks run from here
    │   ├── evals/                    # evaluation harnesses, metrics definitions, scoring scripts, baseline references
    │   ├── experiments/              # run manifests, raw results, per-run analysis — one subdir per run, manifest-bound
    │   └── configs/                  # shared run/test/eval configuration (hyperparameters, environment specs)
    ├── reports/research-report.md
    ├── manifests/artifact-manifest.json   # immutable locations + hashes of every versioned artifact, including large outputs stored outside Git
    └── project-state.json            # the Lead's live ledger: stage, outer_cycle, inner_attempt, budgets, HOLD/SUSPENDED status
```

`change-and-progress-logs/` is the centralized governance hub of the research project: charter, planning, reviews, and decisions live nowhere else, and `index.md` is the master table — content and acceptance owned by the Lead, mechanical updates performed by `okf-writer` — (one row per charter version, plan version, review verdict, decision, and cycle, each pointing at its artifact) so any state — past or present — is retrievable for audits, session resumption, and REPORT_GATE confirmation evidence. The hub is an OKF v0.2 bundle: the two local v0.2 specification copies are verified identical, so either is authoritative (the older v0.1 skill copy is background only). Within the hub, markdown concept records, indexes, and logs are OKF-validated bundle content; `cycle-decision.json`, `artifact-manifest.json`, and `project-state.json` are machine-owned JSON artifacts — indexed, never rewritten as concepts — and the Lead tasks `okf-writer` with all concept-record, index, and log writes (with `validate_okf.py` bundle-check before publication) and tasks `okf-reader` with evidence retrieval; the Lead keeps direct ownership of `project-state.json` counters and git checkpoints.

The project workspace is the durable source of truth. Pi subagent session/run artifacts and temporary outputs are useful for consultation history, but their retention is configurable and they are not a permanent research archive. The Lead copies or references durable findings in project records before relying on them. Large datasets, binaries, and experiment outputs may be stored outside Git in content-addressed artifact storage; manifests should record immutable locations and hashes.

### 7.3 Research knowledge organization

I recommend four knowledge categories.

| Knowledge category | Contents |
|---|---|
| Research literature | Papers, theories, concepts, related work |
| Project knowledge | Goals, hypotheses, decisions, constraints |
| Experimental evidence | Methods, configurations, outputs, metrics |
| Operational knowledge | Tools, procedures, previous failures, research practices |

The Lead should retrieve only the knowledge needed for the active task.

The Advisor should receive relevant knowledge through the consultation package and selective artifact access.

Avoid building a complicated knowledge graph in the initial implementation. A searchable artifact store, structured metadata, and reliable source references are sufficient to begin.

### 7.4 Claim-to-evidence traceability

Every important research claim should have an associated evidence record.

```json
{
  "claim_id": "CLAIM-012",
  "statement": "Prompt variation affects performance",
  "status": "supported_with_limitations",
  "evidence": [
    "EXPERIMENT-005",
    "PAPER-014"
  ],
  "limitations": [
    "Only three models evaluated",
    "Task family restricted to mathematical reasoning"
  ]
}
```

The Lead must not convert a plausible hypothesis into a verified fact merely because the Advisor agrees with it.

---

## 8. Host orchestration, state, and execution contracts

The Research Lead is the host/main Pi agent. It owns the project state and coordinates its own work with Research Advisor and Engineering Worker child runs. Pi conversation history and child sessions are useful execution context, but the durable research record belongs in `research-projects/<project-id>/`.

- **Research-domain state** includes the active stage, approved protocol, tasks, evidence, decisions, budgets, reviews, and completion status. The Lead records it in `project-state.json` and the versioned artifacts it references.
- **Pi execution state** includes Advisor and Worker child run IDs, session references, status, and usage. `pi-subagents` manages this child-run state; it is not a permanent substitute for the research-domain record.

Starting a new host session requires loading the Lead prompt again with the documented `--append-system-prompt` command, then reading the project state and resuming from its artifacts. Pi's subagent runtime does not persist the Lead's research-stage state as a workflow engine would.

### 8.1 Project and task records

The project record should track:

- Project ID, research direction, objectives, constraints, and resource budget (including `max_outer_cycles` in [3, 5]).
- Active stage, `outer_cycle` / plan version, `inner_attempt`, approved protocol version, task dependencies, acceptance criteria, and attempts.
- Research questions, hypotheses, decisions, evidence references, and artifact hashes.
- Advisor consultations and review verdicts, including relevant Pi child run IDs.
- Beads task IDs linked to issued Worker and pool assignment records, including attempts and decisions, under [§8.9](#89-assignment-ledger-and-delegation-lifecycle). Do not mirror Beads backlog fields into project state.
- Human decisions, unresolved findings, and project completion status.

The Lead maintains this record. Stage approval refers to an immutable/versioned deliverable manifest; distinguish submitted artifacts from approved artifacts. A task is complete only when its acceptance criteria and verification evidence are recorded. An Advisor child run marked `complete` means only that the consultation settled; it does not mean the research is scientifically valid or accepted. A Worker or pool run marked `complete` means only that the run settled; see §8.9.4 for assignment acceptance.

### 8.2 Advisor consultation and stage review

The Lead performs a structured readiness assessment for each meaningful task and records the conclusion and evidence in the project state. It investigates bounded factual/technical uncertainty directly, consults the Advisor for material conceptual or methodological uncertainty, and pauses for human input when authority or essential information is missing.

Launch the Advisor directly through Pi Subagents with a focused task and fresh context. For example, the host can call `subagent` with `agent: "research-advisor"`, the consultation/review brief as `task`, and `options.context: "fresh"`. The Advisor receives the brief and its own allowed tools; it does not automatically inherit the host's conversation or system prompt. Supply artifact paths/IDs and ask it to inspect primary evidence. If a call runs in the background, the Lead must collect and inspect the completed result before relying on it.

Use the Section 4.4 decision contract for gate reviews. Where appropriate, request Pi structured output with a matching schema and validate the verdict, gate name, and `review_target` manifest version as §4.4 requires; fail closed on any mismatch. A valid schema or successful child run proves only response shape/run completion—not that the claims are true. Record the consultation result in project decisions/reviews before proceeding. On a failed or invalid Advisor result, HOLD the dependent gate and apply §4.4's bounded re-request policy. Escalate if recovery is exhausted or the Advisor is confirmed unavailable; neither condition authorizes a substitute or gate advancement.

### 8.3 Assignment and acceptance

For Worker and pool assignments, see the [assignment brief (§8.9.1)](#891-resource-model-and-assignment-brief) and [result verification and acceptance contract (§8.9.4)](#894-result-verification-and-acceptance). Advisor and OKF results retain their own contracts (§4.4, §8.7).

### 8.4 Loop-aware progression and host-session resumption

The Research Lead follows a loop-aware progression, not a linear stage chain. Outer-cycle count, inner-attempt count, progress verdicts, and termination status are first-class project state. This table is authoritative for every gate: if prose elsewhere suggests a different next step, this table governs.

```text
CREATED -> SCOPING -> PLANNING -> PLAN_GATE (plan v_n approved?)
        -> [ INNER LOOP: IMPLEMENTING ⇄ EVALUATING ]
             (valid PLAN_GATE readiness before full evaluation;
              inner_attempt = 1, 2, ... under plan v_n)
        -> INNER_EXIT_GATE (evidence package: complete or
             explicitly incomplete-for-diagnosis?)
        -> ANALYZING -> CYCLE_GATE (Advisor-reviewed interpretation,
             limitation diagnosis, progress verdict, route)
             |-> report route  -> REPORTING -> REPORT_GATE -> COMPLETED
             |-> replan route  -> PLANNING (v_n+1; only if outer budget remains)
             |-> HOLD          -> triage; resume or convert to SUSPENDED
             |-> terminal stop -> SUSPENDED + status report
```

| Gate | Verdict | Legal routes → next state |
|---|---|---|
| PLAN_GATE (protocol) | `approve` of plan v_n | `continue` → IMPLEMENTATION under the approved protocol; not authorization for full evaluation |
| PLAN_GATE (readiness) | `approve` of the built baseline and passing required tests | `continue` → full evaluation; required initially and whenever readiness coverage lapses (§5.3) |
| PLAN_GATE (protocol) | `revise` | `remediate-plan` → PLANNING in the same authorized cycle, then review the revised protocol manifest (max 2 rounds, then HOLD + escalate) |
| PLAN_GATE (readiness) | `revise` | `remediate-implementation` → IMPLEMENTATION within the approved protocol, then review the revised readiness manifest (max 2 rounds, then HOLD + escalate); if the repair needs a protocol change, use the diagnosis-only INNER_EXIT_GATE route instead |
| PLAN_GATE (either phase) | `inconclusive` | `gather-evidence` → bounded evidence + one re-review, then HOLD if unresolved |
| PLAN_GATE (either phase) | `block` | HOLD triage immediately; SUSPENDED + status report only if confirmed unresolvable |
| INNER_EXIT_GATE | `approve` (complete package) | `continue` → ANALYSIS |
| INNER_EXIT_GATE | `approve` (diagnosis-only package) | `continue-to-diagnose` → ANALYSIS; package is barred from supporting success claims |
| INNER_EXIT_GATE | `revise` | `remediate-implementation` → bounded inner-loop rework, then re-review (max 2 rounds, then HOLD + escalate) |
| INNER_EXIT_GATE | `inconclusive` | `gather-evidence` → bounded evidence + one re-review, then HOLD if unresolved |
| INNER_EXIT_GATE | `block` | HOLD triage immediately |
| CYCLE_GATE | `approve` + objective met | `report` → REPORTING |
| CYCLE_GATE | `approve` of a justified `replan` proposal + objective unmet + neither stop predicate fired | `replan` → authorize and charge cycle n+1, then PLANNING → PLAN_GATE protocol review for v_n+1 |
| CYCLE_GATE | `approve` + objective unmet + neither stop predicate fired + no approved, justified `replan` proposal | HOLD for triage; no new cycle without a justified proposal and matching approval |
| CYCLE_GATE | `approve` + objective unmet + cap or early-stagnation predicate fired | SUSPENDED + status report directly (§8.6) |
| CYCLE_GATE | `revise`, fix stays within plan (even at cap or early stagnation) | `remediate-implementation` → bounded inner-loop rework, then INNER_EXIT_GATE → ANALYSIS → CYCLE_GATE re-review; HOLD + escalate if required rework exceeds remaining attempt or revise limits |
| CYCLE_GATE | `revise`, fix requires a plan change + neither stop predicate fired | `remediate-plan` → draft proposed v_n+1 while still in cycle n, then return to CYCLE_GATE with a new versioned submission (bounded revise rounds); no PLAN_GATE, implementation, or charge for the draft |
| CYCLE_GATE | `revise`, fix requires a plan change + cap or early-stagnation predicate fired | SUSPENDED + status report preserving the unresolved findings; no draft-to-implementation route and no success claim |
| CYCLE_GATE | `inconclusive` (even at cap or early stagnation) | `gather-evidence` → bounded evidence + one re-review, then HOLD + escalate if unresolved |
| CYCLE_GATE | `block` (even at cap or early stagnation) | HOLD triage immediately → SUSPENDED + status report only if confirmed unresolvable or the human so decides |
| REPORT_GATE | `approve` | `complete` → COMPLETED (final research report: executive summary, read alone, preserves the main limitation, decision-relevant negatives, and the action boundary; Advisor confirms consistency with evidence) |
| REPORT_GATE | `revise` | `remediate-report` → REPORTING, then re-review (max 2 rounds, then HOLD + escalate) |
| REPORT_GATE | `inconclusive` | `gather-evidence` → bounded evidence + one re-review, then HOLD if unresolved |
| REPORT_GATE | `block` | HOLD triage immediately; SUSPENDED + status report only if confirmed unresolvable |
| Any gate | no-verdict (invalid output, stale manifest, failed/unavailable Advisor), even at cap or early stagnation | HOLD + bounded re-request (max 2); escalate when recovery is exhausted or the Advisor is confirmed unavailable |

After cycle 1 is initialized, only `CYCLE_GATE approve/replan` increments `outer_cycle` and resets `inner_attempt`. Record the authorized cycle decision ID, reviewed manifest, and charge before beginning the new cycle's planning; reconcile these on resume so the same authorization is never charged twice. A failed PLAN_GATE does not refund the charge. Draft revisions do not change the active plan version, start a cycle, or reset counters. Inner-attempt exhaustion does not stop the project by itself: when no gate HOLD prevents progression, submit a diagnosis-only INNER_EXIT_GATE package rather than skipping ANALYSIS or claiming success. The Lead's instructions and project state define this policy; Pi does not automatically prevent the host model from skipping a step. Resumption uses the project state (including loop counters, HOLD/SUSPENDED status, and the latest `cycle-decision.json`) and artifact manifest, then checks the prior Advisor review/run evidence before continuing. If state and evidence disagree, stop and reconcile rather than infer approval.

**Precedence.** Check for an applicable safety, authority, or project-resource HOLD as soon as it surfaces. Otherwise use the validated CYCLE_GATE verdict: `block`, `inconclusive`, and no-verdict keep their respective routes regardless of the predicates. On `approve`, validated objective achievement takes `report` before considering either stop predicate, even at the cap. On `revise`, budgeted repair within the same plan remains allowed. Recheck the predicates on the resulting evidence and update the progress verdict for the same cycle, not a new one. Drafting or re-reviewing a next plan does not bypass either predicate.

**Termination enforcement.** The charter sets `max_outer_cycles` (integer in [3, 5], default 4; human-adjustable within range). The two stop predicates are the charged cycle count reaching that cap and the early-stagnation rule (default 2 consecutive `stalled`/`regressed` cycles with no credible new lever, charter-adjustable). Either forbids `replan` at CYCLE_GATE, not execution of the already authorized final cycle. The table determines whether to remediate, HOLD, or convert to SUSPENDED. Counter or objective-checklist output alone cannot supply a verdict or choose a route. A SUSPENDED stop produces a status report (what was tried, what failed, preserved evidence); it never produces an approved final research report.

Pi run/session state helps recover Advisor consultations and inspect their results, but the host Research Lead's conversational state is not a durable workflow engine. A new host session reloads the prompt file, reads the project state, and resumes explicitly. Do not claim automatic transactionality or indefinite recovery for the whole research cycle.

### 8.5 Bounded autonomy and budgets

Use explicit project-level limits for:

- Outer cycles: `max_outer_cycles` in [3, 5] (default 4), recorded in the charter; inner attempts per cycle (bounded, e.g. set per project).
- Gate revise rounds (default max 2) and consultation/evidence retries (limits in §4.4 and §8.4): track separately per gate, PLAN_GATE phase, and cycle. A revised manifest does not reset these counters. A review round does not itself charge a loop attempt.
- Advisor consultations and repeated reviews.
- Worker and pool assignments: attempt accounting and recovery under §8.9.3. Work packages have a soft deadline (wrap up and return `PARTIAL` if unfinished) and a hard cutoff (host-handled, not dependent on a final child response). Other pool assignments still have explicit time/usage limits.
- Experiment runs and wall-clock duration.
- Model token/cost usage and external API expenditure.
- Sandbox CPU, memory, storage, and network use.

The Research Lead tracks these limits in project state. Pi Subagents can report child-run usage and accept per-run controls, but such controls do not replace external compute/API quotas or guarantee stopping all already-running work at a budget boundary. A hard tool budget can block needed operations, and deadline termination can interrupt a mutation. Prefer narrow tasks, explicit checkpoints, external resource quotas, and project-level accounting.

When a limit is reached, stop the work it governs. Assignment and gate limits follow §8.9.3 and §8.4–§8.6; project-wide resource exhaustion HOLDs the project and requires a director decision. Report completed work, unresolved issues, consumed resources, and the next decision at the appropriate scope. No instruction should force a positive research conclusion when evidence is insufficient.

### 8.6 Director communication contract

The human research director governs; the Lead keeps them governable. The director should be able to tell in one read what changed, why it matters, whether they must act, and what the Lead will do next. Upward communication has a fixed shape, not ad-hoc prose:

- **Standing brief (a dated view, not a second ledger).** `change-and-progress-logs/director-brief.md` is the executive summary: objective status, cycle/progress, spend-vs-budget, blockers, pending decisions. Refresh at every CYCLE_GATE and REPORT_GATE, and also on any new/closed/superseded director decision, material change in run status or research conclusion, or budget hold. Start with as-of timestamp and current stage, then what changed and why it matters, decision needed or none, next checkpoint. Link to state, evidence, and decisions instead of duplicating them. For spend, show source, timestamp, and coverage; distinguish recorded spend, estimates, and unknown external charges — the director's own tools remain the monitoring channel. At kickoff, ask what should interrupt them and what tradeoff to prioritize on borderline evidence; revisit after the first consequential decision or on feedback ("too late", "too much detail"). Preferences change delivery only — never the charter, never escalation. Never promise timed check-ins or monitoring while the host is inactive unless demonstrated.
- **Tag by who must act, not by lifecycle state.** `DECISION-REQUIRED` when authority or essential information must come from the director — the run parks with no dependent progression until decided. `FYI` when the Lead owns the next action, even for a serious incident (“evaluation paused; reconciling the workspace, will retry within the existing cap — no action needed”). Record the fault either way. A HOLD for evidence, re-review, rework, or bounded re-request is FYI unless it needs the director; a HOLD that needs director authority (e.g. charter change, additional project resources, or a decision on a blocker the Lead cannot resolve) is DECISION-REQUIRED. Escalate on real authority boundaries or exhausted recovery, never merely on the first error.
- **Scope child failures by dependency.** An optional failed assignment blocks only work that depends on it; independent work can continue if permissions, budgets, and workspace integrity allow. The Lead may retry within the cap, reassign under §3.5, or drop optional work with the gap recorded. Notify promptly in-session for a failed mandatory call, a material incident, or needed director action; otherwise include an optional failure in the next status update. Apply HOLD at a dependent gate if a required call or required evidence is missing; only a valid result from the designated reviewer satisfies a mandatory review. HOLD the whole project only for a project-wide blocker, spent project-wide resource budget, or director action that bars all further work. Do not reuse ambiguous workspaces or outputs to keep progressing.
- **Decision requests that are easy to answer.** Put the ask in the first sentence: why now, the viable options with consequences, the Lead's recommendation and what would change it, what happens without a reply. Deadlines only for real cutoffs; otherwise “before the next run.” One decision ID shared across chat, indexed record, and brief.
- **Close the loop.** Distinguish questions and preferences from authorization. Ambiguous reply → one focused question, never guess; clear reply → act, no ceremonial reconfirmation. Read back the effect, not the transcript (“D-014 recorded: narrow to X; Y out of scope; revising plan for PLAN_GATE before implementation”). Close or supersede the open entry and refresh the brief. If posting or recording fails, disclose the gap when possible and reconcile by ID on resume — never infer receipt or approval. A stop order is honored before polishing records; distinguish work told to stop from work confirmed stopped.
- **Durable and in-session.** Every DECISION-REQUIRED message is recorded in the hub (`decisions/`, indexed in `index.md`) AND surfaced to the human in-session immediately. In-session alone evaporates; records alone go unread — both are mandatory.
- **Director questions.** Answer from the freshest records and name discrepancies (“the brief predates the timeout; state shows evaluation paused; confirmation not yet recorded”). Say explicitly when the answer is not recorded — never improvise.
- **Final report audience.** Written for two readers: executive summary for the director (what was found, what it means, what remains open) over a technical body for the record. REPORT_GATE confirms the summary, read alone, preserves the main limitation, decision-relevant negatives, and the boundary on what the director should do with the finding.

**SUSPENDED conversion authority.** The Lead can convert to SUSPENDED with a status report in the cap/early-stagnation cases specified in §8.4, after triage confirms an unresolvable blocker, or on the director's stop decision. The cap alone does not override a gate verdict. The director alone decides to cease, narrow, or authorize additional resources on a project-resource HOLD; resource exhaustion alone never converts without that decision.

### 8.7 Knowledge-service delegation

The Lead delegates documentation mechanics to the two knowledge services (§2.4) and keeps judgment, state, and checkpoints. Standing rules:

- **Reader for evidence assembly.** Task `okf-reader` with pre-gate evidence gathering (“minimum sufficient evidence for CYCLE_GATE on X”) and mid-run director questions. Its RESULT.md JSON carries the searched scope — never treat a no-match as absence beyond that scope. Gaps are Lead investigation tasks, not stoppers-by-default and never silent skips at gates.
- **Writer for record mechanics.** Task `okf-writer` with decision records, brief-refresh mechanics, index/log updates, and review-record filing, stating exact intended changes and scope. On `committed`, spot-check before gate reliance; on `needs_review`/`rejected`, triage (supply evidence, narrow scope, or record the conflict) — never silently override or fabricate missing metadata. The writer never commits; git checkpoints stay the Lead's.
- **Content stays the Lead's.** The services shape records; judgments (brief assessments, decision rationale, verdict intake, acceptance) originate with the Lead and pass through the writer as content, not as service inference.
- **Validate results, not just files.** Name the entry points: writer output is validated with `validate_okf.py` (bundle check on a staged copy before publication) and its result envelope with `validate_result.py`; reader output with `validate_result.py` against its RESULT contract. The §10.7 `okf-gate-precheck` bundles these plus the created-list/index-rows-vs-disk reconcile into one gate check. The Lead additionally checks every returned result against the request and target revision (right files, right versions, searched scope as stated). A malformed or stale result, a failed or unavailable validator, or missing **required** evidence holds the dependent gate; an explicitly nonessential gap may stand open with its scope recorded. The Advisor still inspects primary evidence — a structurally valid result never establishes sufficiency, freshness, or truth.
- **Serialize hub mutations.** At most one in-flight hub mutation per project: bind each writer operation to a base revision and request ID, validate before publishing, and checkpoint the verified records plus project state before advancing the gate. `committed` is a service publication outcome, never a Git commit. On interruption, reconcile or quarantine the partial update before retrying — never advance a gate on an ambiguous checkpoint. Enforce single-session ownership of the hub (or a lease if multiple sessions can write); concurrent assignment writes require isolated worktrees (§8.9.3).
- **Service-outage fallback.** The Lead↔director path stays direct and never waits on a service: urgent notices, stop-order handling, and authorization interpretation go chat-first, with the hub filing disclosed as pending and reconciled by decision ID on resume. No dependent progression until the filing lands. For current-status questions, compare reader provenance/timestamps against Lead-owned live state and say which is newer. A recoverable child failure is FYI; DECISION-REQUIRED follows only when recovery is exhausted or human authority is needed.

### 8.8 State-driven awareness (data structures over recall)

The Lead must never rely on its context window to know where the project stands. `project-state.json` is a formal state-machine snapshot, and every awareness question is answered by derivation, not recollection:

- **Schema (source of truth, written only by defined writers).** Identity (`project_id`, `protocol_version`, charter ref); lifecycle (`stage`, `outer_cycle`, `inner_attempt`, `plan_version`); per-cycle gate records (gate, phase for PLAN_GATE, verdict, target manifest, rounds used, timestamp; separate protocol and readiness records); objective checklist (each success criterion → `untested | partial | met | failed` + evidence refs); blockers and HOLD/SUSPENDED status (reason, since, resume conditions); budgets (consumed/remaining per class); consultations (IDs, status, run IDs); links to assignment records (see [§8.9.2](#892-ledger-operations-and-retrieval)); decisions (open/closed). Counters and machine fields are written only by the Lead's direct edits and `ledger advance`; concept records live in the hub, never here.
- **Derivations (computed views, never hand-edited).** `ledger status` renders the one-screen view: stage, cycles used/remaining, open blockers and decisions, and per-gate readiness (verdict valid + target fresh + rounds remaining). `ledger next` lists *candidate* next actions with their eligibility basis — candidates only, the Lead selects. `ledger progress` rolls up the objective checklist and the per-cycle trend (`advanced | marginal | stalled | regressed` sequence). `ledger termination-check` supplies predicate information; the Lead applies verdict and phase precedence under §8.4. A route label from a tool is a candidate, not authorization. Every derivation carries its generation timestamp and source revision; a stale view is labeled stale, never silently trusted.
- **Invariants checked on every read.** Counters monotonic; no gate recorded passed without a valid verdict on a fresh target; no dependent progression while a gate HOLD is open except defined triage transitions, and no project progression during a project HOLD; every `met` criterion backed by an evidence ref. Violations are flagged for Lead triage — never auto-repaired, never silently passed.
- **Consumption contract.** At session start, resume, and before every gate, the Lead runs `ledger status` (and `progress`/`freshness-flags` where relevant) instead of reconstructing state from memory or chat history. Consult Beads for task discovery and use the project ledger for run recovery and evidence validity (§8.9); neither view substitutes for the other. Files stay the source of truth; derivations are cached views. What stays judgment: whether evidence supports a verdict, route selection among legal options, diagnosis, acceptance, and everything addressed to the director.

### 8.9 Assignment ledger and delegation lifecycle

This is the authoritative workflow for Worker and general pool assignments. The Lead owns routing (§3.5), dispatch, verification, and acceptance. Beads manages tasks; the project ledger records what was authorized, what ran, and what the research may rely on. Neither schedules agent launches or grants permissions. Pi run state is not the durable research record. Advisor verdicts, architect consultations, and OKF requests retain their own role-specific contracts; shared tracking does not transfer their authority.

#### 8.9.1 Resource model and assignment brief

Beads **v0.49.6 with SQLite** owns operational work items: backlog, title/description, priority, labels, current assignment/status, and task-to-task dependencies. Bind each research project to one explicitly configured database; do not discover a database from a child's worktree or fall back to another project, a different Beads version, or a different backend. Keep this binding in Lead-owned project configuration; do not treat database files or local state as shareable Git artifacts by default.

The existing project ledger owns issued briefs, readiness, dispatch attempts, results, acceptance, integration, and reliance. These are execution and research evidence, not another editable task tracker. Link records by project and exact IDs:

| Record | Required relationships |
|---|---|
| Beads task | Stable Beads task ID scoped to the configured database; one task may have several attempts |
| Assignment and issued brief | Beads task ID, stable `assignment_id` (e.g. `WORK-014`), exact `revision_id`, and previous revision if any |
| Run attempt | Exact assignment revision, unique `attempt_id`, and Pi run ID when known |
| Result | Exact attempt, evidence references, deliverable, and gaps |
| Acceptance decision | Exact attempt and revision; result for acceptance; predecessor when superseding; integration record when available |
| Evidence-use record | Exact acceptance and output, consuming revision or cycle/phase/manifest-specific gate, and requiredness |

A Beads dependency expresses planned work order, not proof that a particular decision or artifact was used. Record actual use in the project ledger without mirroring the task graph. Backlog and document views are derived; do not create another store or duplicate records to represent a view.

Record one assignee per brief. A revision pins the deliverable and exclusions, governing spec and source versions/hashes, dependencies, checkable acceptance criteria, separate read and modify paths, permitted tools/commands/external actions, and time/usage limits. For writes or execution, require a `base_revision` and the exact authorized verification commands (or why none apply); execution-only briefs grant no write paths unless explicitly authorized as write packages. Use soft and hard deadlines as in §8.5. A read-only pool brief can omit inapplicable workspace and command fields; it still pins permitted inputs and expected evidence. Worker-only exceptions, including the skill-plan exception and architect consultations, do not transfer.

The Lead records `READY` for the exact revision only when the scope, inputs, actions, and checks are clear and the required prerequisites are satisfied. Before using a dependency, match the accepted output to the consumer's pins; a prior acceptance does not establish that an output still satisfies a changed consumer. `INVESTIGATE`, `CONSULT`, and `BLOCKED` lead back to reassessment, not dispatch. Freeze the brief on issuance; changes to scope, assignee, input versions, or grants require a new revision and readiness assessment. Record its place in the existing assignment rather than silently broadening scope.

#### 8.9.2 Ledger operations and retrieval

Use the [Beads assignment-management proposal](proposal-for-assignment-management-tools-beads.md) as the implementation checklist for the Pi extension: tool registration, CLI mapping, and integration tests. Verify its command examples against the pinned `bd` v0.49.6 binary. This blueprint remains authoritative for the division of responsibilities, permission boundaries, dispatch recovery, and task closure.

| Operation | Beads task tools (planned project-local extension) | Project execution and evidence ledger |
|---|---|---|
| **CREATE** | `bd_create` captures a work item, not a Pi run. Recover a lost write acknowledgment by exact task ID before retrying; if the ID or match is uncertain, reconcile first. | Persist the issued revision, a prelaunch attempt, the result, and the Lead decision separately. A retry creates an attempt, not a new task. |
| **RETRIEVE by ID** | `bd_get` requires the full task ID and verifies the exact returned ID, including for closed tasks. | Read the exact linked revision, attempt, result, or decision. Do not infer an old brief from the current task fields; Beads `show --as-of` is Dolt-only in this pin. |
| **RETRIEVE by query** | `bd_query` combines native lexical text with structured filters in one query (status, assignee, type, priority range, labels such as `cycle-2`); use explicit status/closed scope and bounded results. `bd_ready` and `bd_blocked` are dependency-aware views. | Resume views surface open intents, unknown launches, and pending verification/integration from ledger records; they do not search or schedule the backlog. |
| **UPDATE** | `bd_update` changes work-item metadata and progress; only guarded `bd_close` records accepted completion or a separately recorded optional drop. Never close a dropped task if that would release a required prerequisite. Use an explicit task ID and checked reason; never use Beads' implicit last-touched target. | Validate named transitions (e.g. `mark-ready`, `attach-run`, `record-hard-cutoff`, `record-integration`) against target and prior state. Corrections supersede rather than rewrite evidence. |
| **DELETE** | Not exposed to the Lead or children by the extension. Do not bypass the tool boundary with a raw `bd` shell or scripted delete. | No delete; preserve historical briefs, attempts, results, and decisions. |

The task extension uses typed semantic tools and the pinned CLI in JSON mode with explicit project binding, argument vectors, and bounded results. Do not expose a generic CLI executor. Native search is lexical, not promised to support stemming, semantic ranking, or historical field snapshots. A Beads `ready` item or assigned status is an operational signal, never §8.9.1 `READY`, launch authorization, or a gate signal. Child tools and indirect `codemode` reachability must not bypass the boundary (§10.6).

The Lead writes evidence through validated ledger operations. For both CREATE and UPDATE, check the expected state and persist the operation ID and receipt with the transition. Exact replay returns the prior receipt marked as a replay, never a new launch authorization or charge; reusing the ID with different input conflicts. Beads updates, Pi launches, Git checkpoints, and project-ledger writes are not one transaction; reconcile their exact references on resume. Do not import task state into the evidence ledger to make inconsistent records look synchronized.

#### 8.9.3 Dispatch and recovery

1. **Authorize.** Retrieve the exact Beads task, check its current ownership and prerequisites, and reconcile open attempts in the project ledger. Use the fixed-roster-first routing rule (§3.5), verify the actual launch profile (§10.2), and check `READY`, permissions, and remaining budgets for the issued revision. Never bypass tool-level limits (§10.6).
2. **Persist intent, then launch.** Create a unique attempt in `dispatch_pending` with the revision, resolved assignee/profile reference, workspace reference where applicable, deadline, and a reserved attempt slot. Only the same uninterrupted Lead invocation receiving the fresh reservation may submit this intent once; a receipt replay, a stored intent, or a resumed session is not permission to submit it. Include the Beads task reference and assignment, revision, and attempt IDs in the fresh brief sent through `subagent`. Attach the returned Pi run ID once bound to that attempt, confirm launch, and track observed status under §2.3. Retain known launch failures; they are not results. Charge at most one package slot per intent that was sent or might have been sent. Release a reservation only when non-dispatch is established. A revised brief does not reset the assignment's retry budget; project and research-loop limits remain separate (§8.5).
3. **Reconcile before retry.** On resume, retrieve open intents, run references, and acceptance/integration records. If the run ID is absent and dispatch cannot be ruled out, record `launch_unknown`. Attach a discovered run only on an unambiguous match using identifiers and runtime evidence verified on the pinned deployment; an agent name or timestamp alone is not a match. If no reliable match is available, keep the attempt unresolved and block affected work under §8.6. Do not blindly relaunch or promise exactly-once dispatch.
4. **Reconcile effects.** Default to one active writer per workspace across Worker and pool. Concurrent writes require isolated worktrees (one per package) and Lead-controlled integration in recorded order against each recorded base revision. Before retrying, reassigning, or reusing an affected workspace, confirm the prior attempt can no longer modify it, compare against the base, and isolate unaccepted changes and other unverified effects. No new attempt while prior execution or its effects remain ambiguous for that work. Record a hard cutoff and the no-usable-result outcome separately from observed execution state; a timed-out child may still be running. A stop request is not proof of termination. The Lead also accounts for authorized external effects before retrying.
5. **Recover within scope.** Correct an underspecified brief via a new revision, fix tooling within existing authority, or consult the Advisor for in-plan uncertainty. A change to the approved plan routes through diagnosis-only INNER_EXIT_GATE and ANALYSIS (§8.4). At the package limit, stop retries; record the gap if dropping optional work, or HOLD and escalate according to dependency and authority (§8.6). Never accept late output as the result of a newer attempt.

#### 8.9.4 Result verification and acceptance

The assignee stays within granted paths and operations and returns a structured result echoing the `assignment_id`, `revision_id`, and `attempt_id`. Preserve the result or versioned evidence references in project storage, not only Pi's temporary output.

- **All Worker and pool results:** return `status` (`SUCCESS | PARTIAL | BLOCKED`), `source_versions` actually used, `deliverable`, `evidence_refs`, and `gaps`. Use empty lists for inapplicable evidence or gaps and a null deliverable when blocked with nothing to return. `PARTIAL` says what was done, verified, and not attempted. `BLOCKED` names the blocking fact, what was tried, and the smallest unblock.
- **Write or execution results:** include affected paths with versions/hashes where applicable, deviations, follow-ups, and observed output for each authorized verification command (verbatim or as an immutable evidence reference), or an explicit `not-run` with reason. A claimed pass without evidence does not satisfy a required check.

Treat missing, malformed, timed-out, or wrong-ID output as no usable result for that attempt; record the failure and preserve traceable evidence without relying on it. A result arriving after timeout or replacement is retained against its original attempt but cannot complete the current work. Compare the reported sources with the pins and verify suitability for the intended decision. A deliberately pinned historical source is not stale merely because a newer version exists. Reject missing required evidence and stale or unapproved inputs. `PARTIAL` and `BLOCKED` do not complete the assignment; scope and verify any usable subset separately with provenance.

The Lead inspects deliverables and evidence, re-runs key checks where practical, and records acceptance or rejection with rationale. No dispatch acknowledgment, Pi `complete` state, or child `SUCCESS` constitutes acceptance. Accept only a verified result for the active revision and eligible attempt. For a workspace-changing delivery, record the accepted revision or artifact hashes and the verified Git integration checkpoint (P9) before making the output available to dependents. If interrupted between acceptance and the checkpoint record, reconcile the exact commit and diff before recording integration or retrying; a verified but unintegrated result does not unblock dependent work. For delivery without workspace changes, record the durable evidence location before dependent use. Only then close the linked Beads task as accepted, with a reference to the decision. If the ledger is settled but the Beads close is missing, reconcile and close by exact ID; if Beads is closed without matching evidence, reopen or block the task for reconciliation and refuse downstream reliance. Assignment acceptance cannot substitute for a required role call or Advisor gate verdict (§4.4, §8.4).

Record actual dependent use against the exact acceptance decision and output; a planned dependency without that pin is not evidence of use. When a decision supersedes an acceptance, preserve the old result, decision, and checkpoint for audit, but stop new reliance on that decision. Flag affected assignment revisions, derived evidence, and gate submissions for revalidation, including downstream chains of recorded use. Do not silently substitute a newer result or retroactively rewrite a verdict. Resume affected work only after its input pins and evidence are revalidated and any required gate is reviewed against the corrected submission. A replacement acceptance needs its own availability evidence; the old integration record alone cannot unblock it. Reopen or block the Beads item when operational status needs correction, but hold affected evidence use even if the Beads update fails.

---

## 9. Scientific rigor and evaluation policy

Research validity must be treated separately from operational task completion.

A research task can execute successfully while yielding scientifically invalid results.

### 9.1 Research design requirements

Every empirical study should define:

**Research question:** What is being investigated?

**Hypothesis:** What relationship or effect is predicted?

**Competing explanations:** What other mechanisms could explain the observations?

**Experimental unit:** What is sampled, assigned, and measured?

**Independent variables:** What is deliberately changed?

**Dependent variables:** What outcomes are measured?

**Controls:** What variables must remain comparable?

**Baselines:** What established or simpler approaches are used for comparison?

**Validity criteria:** What would make the evidence credible?

**Falsification criteria:** What observations would weaken or reject the hypothesis?

### 9.2 Preferred evaluation hierarchy

Use the strongest practical verifier for the task.

| Evaluation mechanism | Typical use |
|---|---|
| Deterministic assertions | Algorithms, structured outputs |
| Reference implementations | Numerical and software tasks |
| Executable tests | Code generation, tool behavior |
| Gold-standard datasets | Extraction, classification, factual tasks |
| Statistical comparison | Stochastic model behavior |
| Expert-validated rubrics | Open-ended research and judgment |
| LLM-as-a-judge | Scalable preliminary qualitative assessment |

LLM-as-a-judge should not be the exclusive source of truth for claims that can be verified deterministically.

### 9.3 Evaluation-specific controls

For LLM experiments:

- Record exact model identifiers and configuration versions.
- Save prompts and inference settings.
- Record tool and harness versions.
- Use separate development and held-out evaluation data.
- Repeat stochastic experiments when necessary.
- Measure cost and latency as well as quality.
- Avoid unjustified equality assumptions about inference compute.
- Use appropriate paired comparisons and uncertainty estimates.
- Validate subjective graders against independent human or reference judgments.
- Report failures and exclusions explicitly.

### 9.4 Distinguish observation from interpretation

The Lead and Advisor must distinguish:

**Observation**

> Accuracy decreased by eight percentage points under the tested prompt variation.

**Interpretation**

> Prompt variation may affect the model's ability to elicit relevant reasoning procedures.

**Causal claim**

> The accuracy decline was caused by inappropriate activation of a learned heuristic.

The first may be directly measured.

The second is a plausible explanation.

The third requires additional evidence capable of distinguishing that mechanism from competing explanations.

The system must preserve these epistemic distinctions.

### 9.5 Cycle comparability and exploratory labeling

Re-planning may change hypotheses, methods, baselines, metrics, or scope — but charter-level objectives and success criteria stay frozen unless the human authorizes a change. Progress verdicts must compare comparable quantities: a changed metric is not progress evidence against the old one — mark non-comparable results as such and re-baseline explicitly. Development evidence (observed during inner-loop tuning) and confirmation evidence (from held-out evaluation under the frozen protocol) are labeled separately; a `report` route requires confirmation evidence, never tuning observations alone. Any protocol change made after observing primary evaluation results is labeled exploratory unless independently confirmed under a fresh plan version.

---

## 10. Pi implementation architecture

### 10.1 Target platform and runtime

**Use the main Pi session as the Research Lead host, and use `pi-subagents` for the fixed roster and the approved general pool, following the caller boundaries in §11.1.** The initial implementation covers the role definitions under `.pi/agents/` incrementally (Milestone 1: core three; architects, reader, writer seated by Milestone 1 exit probes); it does not include a separate workflow script, a Research Lead child agent, or another agent framework.

| Role/runtime element | Pi implementation | Responsibility |
|---|---|---|
| Research Lead | Host instructions loaded with `pi --append-system-prompt .pi/agents/research-lead/agent.md` | Performs the research and orchestrates stages/Advisor calls/worker assignments in the main session |
| Research Advisor | Custom Pi subagent at `.pi/agents/research-advisor/agent.md` | Provides consultation and independent artifact review through child runs |
| Engineering Worker | Custom Pi subagent at `.pi/agents/engineering-worker/agent.md` | Executes bounded implementation packages and returns observed evidence through child runs |
| Delegation | Existing `pi-subagents` extension and the host's `subagent` tool | Starts, tracks, and returns Advisor and Worker subagent runs |
| Research infrastructure | Versioned project workspace, Git, experiment tools, artifact storage, isolated execution | Durable state, primary evidence, code, datasets, results, and reproducibility |

The Lead's system prompt is the orchestration contract. Pi Subagents supplies delegation and child-run management; it does not encode or enforce the research lifecycle.

### 10.2 Agent-definition files

Use these paths:

- `.pi/agents/research-lead/agent.md`: host-role prompt appended to the main Pi session. Start Pi from the repository root with:

  ```bash
  pi --append-system-prompt .pi/agents/research-lead/agent.md
  ```

- `.pi/agents/research-advisor/agent.md`: Pi subagent definition with YAML frontmatter and the Advisor system prompt. Its canonical runtime name is `research-advisor`.

- `.pi/agents/engineering-worker/agent.md`: Pi subagent definition with YAML frontmatter and the Worker system prompt. Its canonical runtime name is `engineering-worker`.

The Lead prompt is not a child agent and should not be launched with `subagent`. Prefer plain Markdown without Pi subagent YAML frontmatter for this file; the Advisor and Worker use standard subagent definitions like other discoverable children. If the Lead file is nevertheless discovered as a child, exclude `agents/research-lead` from `subagents.agentExcludeDirs` in `.pi/settings.json` (relative to `.pi`); this removes it from the child catalog without affecting direct `--append-system-prompt` loading. Keep fixed-role names reserved; discovery alone does not make an additional agent eligible for general pool work (§3.5). Note the current project `.pi/settings.json` is empty (`{}`): the exclusion, model overrides, and any tool defaults must still be added and their effect verified — list the discovered child catalog before and after, and confirm the Lead prompt loads via the flag in both states.

**Runtime pin and verification checklist.** This design was written against Pi CLI 1.6.0 and `pi-subagents` 0.89.2. Before implementing the prompts, pin the deployed versions and verify each of the following against the running system; every frontmatter field and invocation below is conditional on verification until then:

1. The exact frontmatter keys the deployed `pi-subagents` honors (`tools`, `model`, `thinking`, `systemPromptMode`, `inheritProjectContext`, `defaultContext`, `acceptanceRole`, aliases) — the reference file's keys are examples, not proof.
2. What a fresh child context excludes (host conversation, host system prompt) and still loads (project context files, skills, tool providers) for each child.
3. The effective tool list of each child at launch (inspect, don't assume), including that no delegation-capable tool is reachable from the Advisor, reader, or writer children. Allowed delegation edges are Lead → {Advisor, Worker, architects, reader, writer, approved pool} and Worker → {architects} nested — specify edges first, then verify the deployed `maxSubagentDepth` setting name, scope, and depth-counting convention against the running system so that exactly the Worker→architect edge occurs and nothing deeper; do not assume the setting is honored. Caller-specific denial that is not runtime-enforced is labeled prompt policy, not a restriction.
4. The `agentExcludeDirs` path base and its effect on discovery vs. direct prompt loading.
5. Structured-output support and schema-constraint behavior for gate verdicts (§4.4, §11.2–11.3).
6. The effective provider/model ID and override source for all seven fixed children, resolved from their actual call sites at preflight. An unresolved pin or unapproved fallback does not count as a successful launch.
7. For each selected pool member, compare the actual launch resolution with the operator's approval: canonical name and resolved definition source/version (or digest), effective provider/model and override, and effective capabilities, including inherited tools and tools/model endpoints reachable through `codemode` or another wrapper. Record the verified resolution with the launch attempt (§8.9.3), or with the preflight evidence for a smoke test; per-assignment tools and access may only narrow it. Check this resolution before every launch or retry, including smoke tests. Refuse a changed, ambiguous, or unverifiable profile and require reapproval for changes. Never launch a pool member if delegation is reachable or the verified configuration cannot be pinned or rechecked at dispatch. Smoke-test on first use and after relevant configuration or runtime changes using disposable inputs and workspace; do not add the whole pool to the kickoff smoke test.

The Research Lead's tools come from the main Pi host configuration. Ensure the `pi-subagents` extension and its `subagent` tool are available in that session. The Advisor's frontmatter should set an explicit read-only tool allowlist (for example `read`, `grep`, `find`, `ls`, plus selected read-only evidence providers), project-context inheritance as needed, a separately configurable model, and no nested subagent delegation. The Worker's frontmatter should set a bounded write-capable allowlist (read/inspect tools plus `edit`, `write`, scoped command execution such as `bash`/`codemode`, AND explicit `subagent` — empirically, the `allowNestedSubagents` grant alone does not surface the spawn tool in the child session; the explicit entry is required, and the depth cap remains the enforcement guard), the `implementation-workflow` and `problem-framing-and-autonomous-decision-making` skills, a bounded nested-delegation grant (`allowNestedSubagents: true`, `maxSubagentDepth: 2`), and a separately configurable model. Loading a tool provider/extension and allowlisting its tool are separate configuration steps.

### 10.3 Host-led Advisor delegation

For a consultation or mandatory stage review, the Lead calls `subagent` directly with `agent: "research-advisor"` and a focused `task` containing the decision/review brief, rubric, constraints, and exact artifact paths/IDs. Use a verified fresh child context (see §10.2 checklist: excludes host conversation and host system prompt; inherits only configured project context) so the Advisor assesses the supplied evidence rather than inheriting the Lead's conversation. Where appropriate, request schema-constrained structured output matching Section 4.4 and validate the returned verdict, gate name, and `review_target` before proceeding.

The Lead owns all stage sequencing, task execution, remediation, project-state updates, and direct human escalation. It should invoke one Advisor child per decision/review, consume the result via the Pi subagent result/status mechanism, and preserve useful outcomes in project files. Use asynchronous child execution for long consultations when it keeps the host responsive, but do not treat dispatch acceptance as a completed review.

### 10.4 Host-led implementation delegation

Use the [assignment dispatch and recovery procedure (§8.9.3)](#893-dispatch-and-recovery). Verify Pi's effective launch configuration and fresh-context behavior under §10.2; enforce tool access under §10.6.

Do not add `.pi/workflows/research-lifecycle.js` as a required component in version 1. A reusable `pi-subagents` scripted workflow may be considered later for a well-defined mechanical sequence, but it is not the host's role and must not replace the Research Lead as lifecycle owner.

### 10.5 Suggested initial stack

| Component | Recommendation |
|---|---|
| Host agent | Pi main session with the Research Lead prompt appended at startup |
| Subagent runtime | Pi Subagents extension (`pi-subagents`) |
| Host prompt | `.pi/agents/research-lead/agent.md` |
| Advisor subagent | `.pi/agents/research-advisor/agent.md` |
| Worker subagent | `.pi/agents/engineering-worker/agent.md` |
| Specialist architects | `.pi/agents/{harness,backend,frontend}-architect/agent.md`; Lead- or Worker-nested consults per §2.4 |
| Knowledge services | `.pi/agents/okf-reader/agent.md`, `.pi/agents/okf-writer/agent.md`; Lead-invoked only, §8.7 |
| Agent discovery | Project `.pi/settings.json`; exclude the Lead prompt directory if it would be discovered as a child |
| Lead model | Main Pi session's configured model; selected by the operator |
| Advisor model | Independently configurable in Advisor frontmatter or `subagents.agentOverrides` |
| Worker model | Independently configurable in Worker frontmatter or `subagents.agentOverrides`; strong enough to write correct code and tests, since flawed output costs Lead verification and rework |
| Architect / reader / writer models | Independently configurable per role (frontmatter or `subagents.agentOverrides`); effective provider/model ID and override source recorded at preflight per §10.2 item 6 |
| Source control | Git; use isolated worktrees when concurrent or risky code changes require them |
| Project state and artifacts | Versioned project files plus immutable external artifact storage for large outputs |
| Experiment analysis | Python, pandas, SciPy, and task-specific libraries where appropriate |
| Mechanical checks | §10.7 toolset (`validate-verdict`, `verdict-still-covers`, `okf-gate-precheck`, `ledger`, `preflight`, `freshness-flags`, `smoke-roster`): deterministic, versioned, Lead-invoked |
| Literature sources | Academic search/publisher APIs, official documentation, and repositories through explicitly loaded tools |
| Verification | Tests, executable checks, source provenance, and independent scientific assessment |
| Observability | Pi Advisor and Worker run/session/usage records plus durable project decision and artifact manifests |

The Lead must be capable enough to implement and evaluate real experiments. A cheaper model that frequently generates flawed work may increase total cost through rework and Advisor consultations.

### 10.6 Tool permissions and security

**Research Lead host**

- Uses the main Pi session's filesystem, repository, terminal, research, and experiment tools within the host's configured permissions.
- Uses `subagent` to call the fixed roster and approved pool within their respective task and permission boundaries (§3.5, §11.1).
- Owns implementation acceptance and project artifact changes.

**Research Advisor subagent**

- Read-only access to artifacts, source, tests, results, and literature relevant to the task.
- Selected read-only retrieval and optional isolated analysis tools.
- No `write`, `edit`, or general-purpose shell access; no nested subagent delegation.

**Engineering Worker subagent**

- Read/inspect tools plus `edit`, `write`, and scoped command execution (`bash`/`codemode`) limited to assigned paths, tests, and verification commands; the `implementation-workflow` and `problem-framing-and-autonomous-decision-making` skills for major-task execution.
- No access to project plans, decisions, reviews, or state records — except the package's own plan file under `.pi/plans/` when the package explicitly grants it; bounded nested delegation only (`allowNestedSubagents`, depth ≤ 2, skill-directed, Worker→architects only, never to the Lead role, never Worker→Advisor) — no unrestricted fan-out.
- Returns the [§8.9.4 structured result](#894-result-verification-and-acceptance) for every assignment, including blocked or partial work; reports blockers in the returned result (no heartbeat channel in version 1), never to the human directly.

Pool access is the intersection of the approved profile and the assignment, including read inputs, paths, commands, budget, and external actions. Apply the Worker work-package controls to pool writes and execution without granting Worker-only exceptions. For `codemode`, verify that reachable tools and model endpoints respect the same limits; enforce them on the underlying calls, not in the script's instructions. If confinement cannot be verified, do not use the capability beyond the disposable exercises in §13. Apply sandboxing, filesystem/network boundaries, secrets management, resource quotas, restricted external side effects, prompt-injection defenses, and human approval for irreversible or externally visible actions at the host/tool layer. Pi tool allowlists are not an operating-system sandbox. Retrieved pages, repositories, datasets, prompts, and dependencies are untrusted data—not instructions that may override either role contract.

### 10.7 Deterministic orchestration toolset (mechanics as code)

Judgment stays with the Lead; arithmetic, schema, and comparison move into a small pinned toolset the Lead invokes as authorized commands. Each tool is deterministic, versioned, and recorded as evidence. Tool refusal never physically prevents host advancement (no policy extension in v1) — it makes the violation visible and checkable, and the Lead remains accountable for heeding it.

| Tool | Inputs | Outputs | Guards |
|---|---|---|---|
| `validate-verdict` | verdict JSON, invoked gate and phase if applicable, submitted manifest id/version | pass/fail + enumerated reasons (schema, wrong gate or phase target, stale target) | every gate: PLAN / INNER_EXIT / CYCLE / REPORT (§4.4) |
| `verdict-still-covers` | reviewed manifest and hashes, current manifest and hashes | match/drift + changed references; the Lead evaluates any drift under §5.3 before relying on readiness coverage | gate reliance, especially PLAN_GATE readiness and REPORT_GATE |
| `okf-gate-precheck` | hub bundle root, writer result envelope | clean/dirty + findings (`validate_okf.py`, `validate_result.py`, created-list/index-rows-vs-disk reconcile) | CYCLE_GATE, REPORT_GATE, any writer-dependent progression (§8.7) |
| `ledger` | `show`: project-state section; `advance`: project lifecycle event; `termination-check`: state + charter; `status`/`next`/`progress`: derived views (§8.8); planned execution-evidence operations (§8.9.2) | counters, receipts, predicates, candidate actions, progress and recovery views, exact historical evidence records | CYCLE_GATE charging and termination (§8.4); startup/resume and pre-gate checks (§8.8); execution evidence (§8.9) |
| Beads task tools | Project-bound Beads v0.49.6 SQLite CLI via `.pi/extensions/beads-tools/` (planned) | exact task lookup, combined task search and metadata filters, dependency-aware ready/blocked work, guarded task updates | Operational task management only (§8.9.2) |
| `preflight` | repo root | recorded roster (7 canonical names), effective model + override source per role, depth config, validator availability | kickoff, Milestone 1 exit (§10.2 item 6, §13) |
| `freshness-flags` | hub root, `project-state.json` | flag list (brief as-of vs state, `stale_after` evaluation, reader provenance vs live state) | CYCLE_GATE brief refresh, director Q&A (§8.6–8.7) |
| `smoke-roster` | repo root | per-role launch success + resolved model for the seven fixed children | kickoff, Milestone 1 exit, post-upgrade re-verification |

Shared wiring rules: project-ledger mechanics live in `tools/research-ops/` (Python stdlib); the separate task adapter is a project-local TypeScript Pi extension with a pinned Beads dependency (§8.9.2). Only Lead-invoked ledger write operations write lifecycle and execution evidence; serialize with hub mutations per §8.7. Record tool invocations and results with the tool version. A failure, missing tool, or version mismatch holds the dependent gate when its check is required (§12.4). The prototype `ledger.py` has `validate`, `show`, `advance`, `termination-check`, `status`, `next`, and `progress`, but not the §8.9 execution-evidence contract. Do not add a duplicate task index to it. The extension, full evidence transitions, and other §10.7 tools are not yet built; do not treat prototype tests as conformance.

---

## 11. Agent prompts and contracts

### 11.1 Research Lead host-prompt template

**Role:** Autonomous Applied AI Research Lead, running in the main Pi session.

**Loading:** Start the host session with `pi --append-system-prompt .pi/agents/research-lead/agent.md` from the repository root. This file configures the host role; it is not a subagent to launch.

**Mission:** Transform human research directions into rigorous, reproducible research results while owning the full research lifecycle.

**Responsibilities**

- Own research planning, implementation, evaluation, analysis, and reporting.
- Maintain project state, artifacts, evidence, budgets, and decisions in the research workspace — hub concept records, indexes, and logs via `okf-writer`; `project-state.json` counters and git checkpoints directly.
- Assess readiness and look for independently verifiable pieces before doing substantial work. Delegate every meaningful, self-contained `READY` task with concrete scope and a suitable authorized assignee within budget. Route in-scope work to its fixed role; consider the general pool only if no fixed role covers the task. Record why a task is outside the fixed roster before pool dispatch, or why meaningful work was retained (§3.5).
- Use `subagent` for Lead → `research-advisor` (consultation, gate review), `engineering-worker` (bounded implementation), the three named architects (domain advice), `okf-reader` / `okf-writer` (hub work), and approved general pool members (bounded work, with writes, execution, and `codemode` limited to granted capabilities). The Worker may invoke only the named architects, nested inside a package. Pool members cannot delegate, and no discovered-but-unapproved agent is eligible.
- OKF handoff policy: task the services with mechanics, never judgment — state exact intended record changes and scope; reader RESULT JSON is evidence with a searched scope, never absence-proof; writer `committed` gets a spot-check before gate reliance and `needs_review`/`rejected` gets triage (supply, narrow, or record the conflict), never silent override; writer output is records, never rulings.
- Verify Worker and general pool results against acceptance criteria and re-run key checks where practical; accept or reject the work explicitly.
- Submit completed artifacts for mandatory Advisor review. Require separate PLAN_GATE verdicts for the protocol and the tested baseline; use §8.4 for every gate route and never charge a cycle on a draft replan.
- Integrate advice, verify findings independently, and document unresolved disagreements.
- Ask the human directly when authority, unavailable information, or a material scope decision requires it.

**Reasoning and execution discipline**

- Distinguish facts, inferences, hypotheses, and assumptions.
- Do not fabricate sources, observations, experiment results, or successful executions.
- Prefer primary evidence for consequential claims and preserve negative/contradictory findings.
- Use project artifacts as durable state; do not rely on session history as the only memory.
- Do not advance until the mandatory Advisor review and defined evidence checks are complete.
- Treat this gate as a host-agent obligation; Pi's `subagent` tool does not enforce the research lifecycle automatically.

**Advisor consultation discipline**

- Formulate one precise decision or closely related question set per consultation.
- Supply a compact brief, relevant artifact paths/IDs, alternatives, constraints, and requested output.
- Use a fresh Advisor context and read-only access to the cited evidence.
- Inspect the returned review verdict and findings; Advisor agreement is not proof.

### 11.2 Research Advisor subagent template

**Role:** Principal Research Scientist and Methodological Advisor, invoked as the `research-advisor` Pi subagent.

**Suggested frontmatter** (verify every key against the deployed runtime per the §10.2 checklist before use):

```yaml
name: research-advisor
description: Read-only methodological reviewer for Lead-assigned research consultations and gate reviews. Assesses cited evidence with fresh context and returns structured advice or gate verdicts; owns no decisions, implementation, or acceptance.
model: <independently configured; strong enough for methodological critique>
thinking: high
systemPromptMode: replace
inheritProjectContext: true
tools: read, grep, find, ls
defaultContext: fresh
```

Notes: read-only allowlist plus explicitly approved read-only evidence providers only; no `write`, `edit`, shell, or `subagent` tools. Frontmatter states intent; the enforceable boundary is verified effective tool inspection (Milestone 3).

**Mission:** Improve the theoretical rigor, scientific validity, and intellectual quality of the Research Lead's work.

**Tool and authority boundary**

- Use only explicitly allowlisted read-only tools for research artifacts, sources, code, tests, and results.
- Do not modify files, execute general-purpose shell commands, alter raw data, or launch subagents.
- Advice and review verdicts do not authorize actions or transfer deliverable ownership from the Lead.

**Responsibilities**

- Provide focused theoretical and methodological guidance when consulted.
- Critically assess planning, implementation, evaluation, analysis, and reporting artifacts.
- Identify invalid assumptions, confounds, weak baselines, missing evidence, alternative explanations, and unsupported conclusions.
- Request primary artifacts when the supplied summary is insufficient.
- Return the structured review contract in Section 4.4 for mandatory stage reviews.

**Evaluation discipline**

- Do not agree merely to maintain conversational harmony or infer correctness from the Lead's confidence.
- Distinguish established findings from plausible explanations and speculation.
- Explain why issues matter and specify evidence or correction that would resolve them.
- State uncertainty when warranted; do not represent your review as proof of correctness.

### 11.3 Engineering Worker subagent template

Modeled on `.pi/agents/implementation-workflow-worker/agent.md`: a bounded writer child with an explicit assignment contract. The host owns scope, plans, decisions, phase transitions, and acceptance; the Worker owns only faithful execution of the assigned package and honest reporting of what it observed.

**Suggested frontmatter**

```yaml
name: engineering-worker
description: Bounded implementation worker for Lead-assigned research work packages. Implements only explicitly granted paths, runs the assigned verification, and returns observed evidence or an early blocker. The host owns plans, decisions, reviews, acceptance, and lifecycle routing.
acceptanceRole: writer
model: <independently configured; strong enough for correct code and tests>
thinking: high
systemPromptMode: replace
inheritProjectContext: true
tools: read, grep, find, ls, bash, edit, write, codemode
defaultContext: fresh
```

Notes: the Worker template grants the bounded nested-delegation tools (`subagent` in the allowlist plus `allowNestedSubagents`, `maxSubagentDepth: 2`) for Worker→architect consults only — no `contact_supervisor`, no heartbeat in version 1. Silence is handled by bounded run status plus workspace reconciliation (§8.9.3, §8.5). Loading a tool provider/extension and allowlisting its tool are separate configuration steps. Frontmatter allowlists state intent; the enforceable boundary is the Milestone 3 confinement verification, not this file.

**Role:** Bounded research implementation worker, invoked as the `engineering-worker` Pi subagent.

**Mission:** Implement exactly the assigned work package — code, tests, configs, reproduction commands — and return complete, honest evidence of what was done and observed.

**Tool and authority boundary**

- Edit only granted code/test/config paths; never touch plans, hypotheses, decisions, reviews, state records, or out-of-scope files.
- Delegate only to the three named architects within the package; never call the general pool. Never orchestrate later stages, broaden scope, relax verification, or claim an unrun check passed.
- A `complete` run status reports that the run settled, not that the work was accepted. Return the structured result defined in §8.9.4.

**Responsibilities**

- Implement the package per the assigned spec and acceptance criteria.
- Run the authorized verification commands (including adjacent tests only if authorized) and return observed evidence under §8.9.4.
- Stop and report a bounded `BLOCKED` result when the package is underspecified, the environment prevents verification, or the fix would require changing the research plan.
- Budget the attempt/deadline limit: before it expires, stop starting new work, run verification on what is done, and return the structured `PARTIAL` result with exact state.

**Evaluation discipline**

- Distinguish implemented-and-verified from implemented-but-unverified from not-attempted.
- Report deviations, failures, and negative observations promptly; never convert a failing check into a success narrative.

## 12. Evaluating the research-agent system itself

The system should be evaluated empirically before relying on it for important research.

### 12.1 System-level benchmarks

Use representative research assignments with externally assessable outcomes.

Examples:

1. Reproduce an established prompt-sensitivity result.
2. Implement a published reasoning benchmark.
3. Investigate the causal interpretation of a reported LLM capability.
4. Compare two agent harness designs under fixed evaluation conditions.
5. Perform an ablation study of a retrieval or context-engineering technique.

Include assignments that are intentionally ambiguous, contain conflicting evidence, or require the correct decision to report inconclusive findings.

### 12.2 Compare system variants

At minimum compare:

| Variant | Description |
|---|---|
| A | Lead operating independently |
| B | Lead with mandatory Advisor stage reviews |
| C | Lead with mandatory reviews and uncertainty-triggered consultations |
| D | Full architecture with curated consultation packages and adaptive context |
| E | Full architecture plus Engineering Worker for bounded implementation packages |

This allows the contribution of consultation and context engineering to be estimated separately.

### 12.3 Evaluation dimensions

**Research quality**

- Scientific validity.
- Methodological rigor.
- Factual accuracy.
- Reproducibility.
- Correctness of implementations.
- Quality of conclusions.

**Agent collaboration**

- Value of Advisor interventions.
- Critical defects detected.
- Unnecessary consultations.
- Unresolved issues correctly escalated.
- Advisor-review false acceptance.
- Review-induced regressions.

**Operational performance**

- End-to-end task success.
- Completion without unnecessary human intervention.
- Execution cost.
- Advisor and Worker token consumption.
- Wall-clock latency.
- Recovery after interruption.
- Trace and artifact completeness.

**Context engineering**

- Sufficiency of consultation packages.
- Information lost through compression.
- Evidence expansion frequency.
- Repeated context transmission.
- Consultation effectiveness per unit cost.

Use independently established scoring criteria; do not rely exclusively on either agent to evaluate the quality of its own system.

### 12.4 Failure-injection tests

Test the system against deliberate failures.

| Scenario | Expected behavior |
|---|---|
| Lead misunderstands the question | Detect ambiguity and consult |
| Lead selects an invalid methodology | Advisor rejects or requests revision |
| Advisor approves incorrect code | Automated tests prevent premature success |
| Worker returns unrun checks as passed | Lead verifies evidence and re-runs key checks; rejects unverified claims |
| Ready task fits a fixed role, but that agent is unavailable | No pool substitution; use the applicable fixed-role recovery path |
| Pool profile is unapproved, changed under the same name, ambiguous, or unverifiable | No launch, including no smoke test, until the actual resolution is verified against operator approval |
| Pool returns a wrong assignment, revision, or attempt ID, stale inputs, missing required evidence, or `PARTIAL` | Do not accept the assignment; record the fault or gap, reconcile any effects, and recover within the existing budget |
| Lead resumes with dispatch intent but no recorded Pi run ID | Match the attempt to a run only with reliable evidence; otherwise keep `launch_unknown` and do not blindly retry or start another writer |
| A replaced attempt returns late, or a create/update receipt is replayed | Retain the late result against the original attempt only; an exact replay does not duplicate a resource, charge, decision, or launch authorization |
| An accepted result is superseded after downstream use | Old decision and checkpoint remain readable, but affected evidence and gates are flagged and new reliance waits for revalidation |
| Beads closes a task without a matching available delivery, or the Lead stops after recording integration but before closing the task | Reconcile by exact linked task and ledger IDs. Never treat a closed task alone as accepted; only finish a missing close after proving availability |
| Lead accepts a workspace-changing result, then stops before recording integration | Dependent work remains blocked until the verified checkpoint is reconciled and linked exactly once |
| Lead queries tasks, then opens a historical assignment revision | Beads lexical search and filters use the bound project database. Closed tasks remain retrievable by exact ID; the project ledger returns the old issued brief by revision ID |
| Optional pool assignment times out; mandatory Advisor review separately fails | Block only the optional assignment's dependents; independent work can continue. The mandatory gate HOLDs, and pool output cannot substitute |
| Protocol approved but readiness missing, or baseline coverage lapses | Tests/smoke runs may establish readiness; full evaluation waits for the applicable fresh readiness verdict |
| CYCLE_GATE requests a plan-changing revision | Draft and return to CYCLE_GATE when no stop predicate fired; no charge or PLAN_GATE launch for the draft. Authorize and charge exactly once on a valid `approve/replan`, including after resume |
| At cap or early stagnation, CYCLE_GATE returns `approve`, `revise`, `block`, `inconclusive`, or no-verdict | Approved achievement reports; approved unmet and a `revise` requiring a new cycle suspend with status report; an in-plan `revise` permits only budgeted repair. `block` or no-verdict holds; inconclusive gets bounded re-review and then HOLD if unresolved. None can authorize a new cycle |
| Advisor receives insufficient context | Requests primary evidence |
| Advisor gives contradictory advice | Lead records conflict and seeks empirical resolution |
| Experiment returns negative result | Preserve and report honestly |
| Upward message lacks tag or record | Lead tags every message DECISION-REQUIRED or FYI and records the former; untagged escalations are a process failure |
| Director asks mid-run status | Lead answers from the standing brief and indexed records, or states explicitly what is not yet recorded |
| Ambiguous director reply | Lead asks one focused question, never guesses; reads back the recorded effect; closes or supersedes the entry and refreshes the brief |
| Writer returns `needs_review` | Lead triages: supply missing evidence/authorization, narrow scope, or record the conflict — never silently override or fabricate metadata |
| Reader reports gaps | Gaps become investigation tasks; gates never rely on absent evidence |
| Malformed/stale service result or failed/unavailable validator at a gate | HOLD the dependent gate; an explicitly nonessential gap may stand open with scope recorded |
| Experiment results are inconsistent | Investigate variability and validity |
| Lead host session or Pi process is interrupted | Start a new host session with the Research Lead prompt, reconcile project state/artifacts, and resume explicitly; recover an Advisor child run only when supported by `pi-subagents`, otherwise relaunch from durable evidence |
| Worker run interrupted after changing files but before acceptance | Treat as no-result: reconcile the workspace against the assignment `base_revision`, quarantine unaccepted changes, re-verify from the recorded revision, then retry or reassign — never accept orphaned mutations |
| Project-wide resource budget is exhausted | HOLD, report consumption, and ask the human; only the director decides resume (extended budget), narrow, or cease (→ SUSPENDED + status report) |
| Retrieved document contains malicious instructions | Treat as untrusted content |
| Evaluation data is contaminated | Flag the validity threat and stop affected claims |

---

## 13. Implementation roadmap

### Milestone 1 — Research Lead host prompt, Advisor subagent, and Worker subagent

Implement:

- `.pi/agents/research-lead/agent.md`, loaded into the main Pi session with `--append-system-prompt`.
- `.pi/agents/research-advisor/agent.md` as the Pi subagent definition.
- `.pi/agents/engineering-worker/agent.md` as the bounded-writer Pi subagent definition (modeled on `implementation-workflow-worker`).
- Clear tool boundaries: Lead owns execution, acceptance, and decisions; Advisor is read-only and cannot spawn more agents; Worker is restricted by prompt rules to granted paths, assigned verification, observed-evidence returns, and Worker→architect nested consults only (no Worker→Advisor, no fan-out) — prompt-level only in this milestone (see confinement note below).
- `.pi/agents/okf-reader/agent.md` and `.pi/agents/okf-writer/agent.md` as the knowledge-service definitions (Lead-invoked only; §8.7 delegation contract).
- Project state/artifact layout, the Advisor consultation/review contract, and the Beads/project-ledger linkage (§8.9). Verify the pinned extension in a disposable SQLite database: exact task lookup (including closed tasks), combined lexical/structured filters, and dependency-aware discovery. Exercise one single-writer Worker assignment with interrupted launch and interrupted close, then a read-only pool assignment; verify exact execution-history lookup before adding concurrent worktrees.
- Agent-discovery exclusion for the Lead prompt directory if its format would otherwise make it a child agent.
- The §3.5 delegation rule and a Lead-only handoff to at least one operator-approved pool member through existing `pi-subagents` discovery. In a disposable workspace, exercise authorized `codemode` use and a scoped write for an out-of-scope deliverable (e.g. extracting supplied primary-paper findings into a specified evidence file, not implementing research code or maintaining the OKF hub). Exercise the pool launch, acceptance, and failure cases in §12.4.

**Exit criterion:** The Lead prompt loads in the host session; the Advisor and Worker are discoverable and can be invoked by name; the Advisor returns read-only inspection evidence; the Worker returns structured evidence for granted-path work; the Lead independently routes and consumes consultations and work packages. All seven fixed definitions (advisor, worker, three architects, reader, writer) resolve by canonical name from their authorized call sites, with effective provider/model ID and override source recorded per role — an unresolved pin or unapproved fallback does not count as a successful launch, and all three Worker→architect routes verify. In a bounded exercise, the Lead routes a task covered by the Engineering Worker to that role even when a pool member could do it, and delegates a concrete task outside all seven fixed roles' scopes to an approved pool member and verifies the result. The Lead refuses unapproved or changed pool profiles even for smoke tests. The Beads adapter and project ledger also pass the linked-task, interrupted-dispatch, and interrupted-close checks above; a Beads status alone never unblocks research reliance. This exit is behavioral evidence only: prompt rules are not enforcement. Verify confinement at the named host/tool enforcement point in Milestone 3 before deploying Worker or pool capabilities beyond disposable exercises.

### Milestone 2 — Host-led lifecycle discipline

Implement and test through bounded research exercises:

- The dynamic dual-loop sequence (inner IMPLEMENTATION ⇄ EVALUATION, outer plan-cycle → ANALYSIS → re-plan), loop counters, termination conditions, and mandatory Advisor review instructions in the Lead prompt.
- Readiness checks, separate PLAN_GATE protocol and readiness records, consultation triggers, fresh-context review packets, and bounded revise/HOLD decisions. Exercise the phase separation, CYCLE_GATE charging/stop precedence, and dependency-scoped recovery cases in §12.4.
- Project-state updates, immutable artifact manifests, and resume instructions for a new host session.
- Human clarification/escalation behavior and explicit disclosure that gates are host-agent policy, not application-enforced workflow.

**Exit criterion:** The Lead loops through inner/outer cycles with counter tracking, launches the Advisor at all mandatory gates, records verdicts/evidence and per-cycle progress, honors all three termination conditions (including stopping after the outer-cycle budget is spent), and does not proceed after unresolved blockers during acceptance exercises. This is behavioral evidence, not a hard runtime guarantee.

### Milestone 3 — Research execution tools

Implement:

- Trusted literature/search tools and source provenance.
- Repository and project artifact access.
- Isolated code execution, automated testing, and experiment runner.
- Worker and pool confinement verification: probe denied out-of-scope reads, writes, execution, delegation, and external actions at the named host/tool-layer enforcement point, both directly and through `codemode` where enabled. Verify read scope separately from modify scope, including for a pool profile without write access. Delegation probes include Worker→Advisor, any non-Lead invocation of the knowledge services or pool, and delegation from a pool member. Do not deploy a Worker or pool capability beyond disposable exercises until its applicable confinement probes pass.
- Immutable experiment configurations/results and artifact manifests.
- Explicitly scoped extensions/MCP tools for the host, Advisor, and Worker.

**Exit criterion:** The Lead can implement and reproduce a small empirical study end to end, and the Advisor can inspect the relevant primary evidence read-only.

### Milestone 4 — Scientific evaluation

Implement:

- Experiment versioning and raw result persistence.
- Statistical analysis, uncertainty reporting, and claim-to-evidence mapping.
- Independent validation and formal stage review rubrics.
- Reproducible report generation and final artifact manifests.

**Exit criterion:** Every important reported empirical result can be traced to its experimental configuration and underlying observations; completion of a Pi child run is not mistaken for scientific validity.

### Milestone 5 — Recovery, budgets, and consultation optimization

Implement:

- Tested host-session resumption from durable project state, Advisor-run recovery where supported, and Worker workspace reconciliation (assignment/attempt/run/workspace refs and unaccepted-change quarantine per §8.9.3).
- External compute/API quotas and project-level resource accounting.
- Context package generation, selective evidence expansion, and decision reuse.
- Token/cost attribution and measured evaluation of consultation effectiveness.

**Exit criterion:** The system demonstrates measurable improvements in research quality and resource efficiency while preserving honest failure and inconclusive outcomes.

Do not add a lifecycle workflow script, another standing role, a separate pool scheduler, a large memory service, or a dashboard before evaluation demonstrates that need.

---

## 14. Worked example: Research on prompting and peak LLM performance

**Human research direction**

Investigate the relationship between prompting, domain-specific tasks, and the attainable performance of frontier reasoning models.

**Research objective**

Determine whether prompt optimization primarily improves semantic task specification, capability elicitation, in-context adaptation, or reasoning strategy selection.

### Stage 1 — Planning

The Lead:

1. Reviews empirical literature on prompting, reasoning, and jagged intelligence.
2. Proposes competing causal hypotheses.
3. Defines controlled task families.
4. Selects frontier models.
5. Designs prompt interventions.
6. Establishes baseline and evaluation metrics.
7. Produces the experiment protocol.

The Advisor evaluates whether the interventions genuinely distinguish the proposed mechanisms.

For example, it may identify that supplying additional domain knowledge is not a valid test of pure capability elicitation, because it changes the information available to the model.

The Lead revises the plan accordingly.

### Stage 2 — Implementation

The Lead decomposes the approved methodology: protocol-sensitive pieces stay with the Lead; bounded construction goes to the Engineering Worker as an explicit package — e.g. WORK-001 (prompt-variant generator + semantic-equivalence checks: allowed paths, governing spec refs, acceptance tests, verification commands). The Worker returns files changed plus observed test output; the Lead verifies, accepts explicitly, and only then submits the baseline for PLAN_GATE readiness.

The Advisor inspects the built baseline and observed test results against the approved protocol. Full evaluation starts only after the separate PLAN_GATE readiness verdict approves that baseline.

### Stage 3 — Evaluation

The Lead executes the benchmark and measures:

- Baseline accuracy.
- Optimized accuracy.
- Recovery rate.
- Regression rate.
- Prompt sensitivity.
- Cross-domain transfer.
- Inference cost.
- Statistical uncertainty.

Suppose the first evaluation shows weak exact-match grading confounded by answer formatting. The Lead iterates the **inner loop**: fix the grader (same plan, new `inner_attempt`), re-run, and record per-attempt deltas — without changing hypotheses or metrics.

Suppose the stabilized results suggest that semantically equivalent prompt variations have little effect on easy extraction tasks but substantial effects on unfamiliar reasoning tasks.

**Stage 4 — Analysis.** The Lead compares observations against the competing causal hypotheses and diagnoses the binding limitation of plan v_1 (e.g. sampling variability and reasoning-token budget confound the causal claim). The Advisor challenges the interpretation — asking whether variation in answer formatting, stochastic sampling, or computational budget explains the observations — and reviews the progress verdict and cycle decision. If the diagnosis calls for a design change the current plan cannot absorb (e.g. new controls or task families), the approved `replan` starts outer cycle 2 under plan v_2; if the gate instead requests an in-plan correction, the Lead returns to the inner loop only within the remaining attempt and revise budgets. The loop repeats until the objective is met, an unsolvable blocker appears, or the outer-cycle budget (3–5 cycles) is spent. Any replan that would change the success criteria or research objective itself requires human authorization first (§9.5) — the Advisor cannot approve charter changes.

### Stage 5 — Reporting

The Lead prepares a report that distinguishes:

- Verified observations.
- Supported interpretations.
- Speculative causal mechanisms.
- Limitations of the experiment.
- Practical implications for prompt and context engineering.

The Advisor reviews the claims against the actual experimental evidence.

The final report includes reproducible code, configurations, raw results or accessible manifests, and the evidence necessary to audit its conclusions.

---

## 15. Final design decisions

The initial system should adopt the following decisions.

| Decision | Recommendation |
|---|---|
| Fixed roles | One Lead host and seven named children: Advisor, Worker, three specialist architects, and two OKF services |
| General subagent pool | Operator-approved, Lead-only Pi children for bounded tasks outside all seven fixed roles' scopes; writes, execution, and `codemode` require explicit grants; no standing authority or nested delegation (§3.5) |
| Research Lead | Main Pi session loaded with `.pi/agents/research-lead/agent.md` via `--append-system-prompt` |
| Research Advisor | Read-only Pi child agent at `.pi/agents/research-advisor/agent.md` |
| Engineering Worker | Bounded-writer Pi child agent at `.pi/agents/engineering-worker/agent.md` (nested delegation bounded: skill-directed, depth ≤ 2) |
| Specialist advisors | Pre-existing read-only consultants (`harness-architector`, `backend-architector`, `frontend-architector`); called by Lead directly or by Worker nested; advise only, never gate/decide/implement |
| Primary owner | Research Lead host agent |
| Orchestration | The Lead uses the same `subagent` tool for the fixed roster and the approved general pool (§11.1) |
| Agent autonomy | The Lead must delegate suitable, concrete work (§3.5) and retains decisions and acceptance; children return bounded results without acquiring authority |
| Review enforcement | Mandatory instruction-level gates (verdict/route table §8.4, fail-closed validation §4.4) in the Lead prompt; not application-enforced unless a separate policy extension is added |
| Confidence assessment | Structured readiness records, not arbitrary scores |
| Consultation context | Compact task briefs with expandable primary-artifact references and fresh Advisor context |
| Shared memory | Versioned project artifacts; Pi Advisor/Worker run/session state is execution history, not research source of truth |
| Research validation | Executable checks, provenance, and independent evaluation; Advisor agreement is not proof |
| Human involvement | Lead asks the human directly for material decisions and unresolved exceptions |
| Technology | Pi host session + `pi-subagents` extension; no second orchestration framework or workflow script in version 1 |
| Expansion strategy | Add policy extensions, persistence services, or UI only when evaluation justifies them |

### Final architectural principle

**The system should maximize the amount of scientifically reliable research accomplished per unit of human attention and computational resources.**

The Research Lead provides execution capacity, persistence, and disciplined research operations.

The Research Advisor provides high-value reasoning, theoretical depth, methodological scrutiny, and intellectual challenge.

The Research Lead host prompt and project records provide the lifecycle discipline; they do not hard-block the host from skipping a review. A separate Pi permission/policy extension is required if stage gates must be non-bypassable.

The experiment and evidence infrastructure provides the foundation for determining whether their work is actually correct.

The central measure of success is not how independently the agents converse, how often they agree, or how impressive their final reports appear.

It is whether the system can repeatedly produce useful, verifiable, reproducible research with limited human intervention and a defensible cost.

---

## Technical and research references

- [Pi coding agent documentation](https://docs.pi.dev/latest)
- [Pi Subagents — agent definitions and tool selection](https://github.com/nicobailon/pi-subagents/blob/main/docs/agents.md)
- [Pi Subagents — tool reference](https://github.com/nicobailon/pi-subagents/blob/main/docs/tool-reference.md)
- [Pi Subagents — configuration](https://github.com/nicobailon/pi-subagents/blob/main/docs/configuration.md)
- [Beads - README.md](https://github.com/gastownhall/beads/blob/v0.49.6/README.md)
- [Beads - CLI_REFERENCE.md](https://github.com/gastownhall/beads/blob/v0.49.6/docs/CLI_REFERENCE.md#advanced-operations)

This revision targets the Pi Subagents API described in the referenced documentation. Pin the deployed extension version and re-check agent discovery, direct delegation, model/tool configuration, and child-run behavior when upgrading it.
