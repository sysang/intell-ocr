# System Design Guideline
## Autonomous Research Team for Applied AI: LLM & Agentic Systems

**Version:** 1.1 — Proposed Pi Subagents Architecture

> Filename note: the file retains its historical `blueprint-draft-v1_0.md` name; the heading version above is authoritative.

**Primary objective:** Build an autonomous, evidence-driven research system implemented by a Research Lead host prompt, a Research Advisor Pi subagent, and an Engineering Worker Pi subagent, using Pi's `pi-subagents` mechanism to convert a human-defined research direction into a research roadmap, implemented experiments, evaluated findings, and a rigorous final report.

---

## 1. System objectives and design principles

### 1.1 Mission

The research system operates as a small autonomous research team with three specialized roles:

- **Research Lead:** The operational owner responsible for planning, investigating, implementing, experimenting, evaluating, analyzing, and reporting.
- **Research Advisor:** The intellectual and methodological reviewer responsible for theoretical guidance, problem clarification, critical assessment, and quality assurance.
- **Engineering Worker:** The bounded implementer responsible for writing code and tests to implement Lead-assigned functionality. It executes only explicitly assigned work packages and returns observed evidence; it owns no research decisions.

The human research director provides research directions, goals, constraints, and feedback when necessary.

The three research roles are defined in `.pi/agents/`, but they occupy different positions in Pi:

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

**P1. Closed role set.** Do not create additional Planner, Critic, Reviewer, or Evaluator agents. Planning, criticism, review, and evaluation are functions of the three core roles: the Lead owns execution and decisions, the Advisor owns critique and review, and the Worker owns bounded implementation. Beyond the core three, the team may call only named members in two tiers: (a) three specialist advisors — `harness-architector`, `backend-architector`, `frontend-architector` — for domain expertise: they advise only and never own gates, decisions, implementation, or acceptance; (b) two knowledge services — `okf-reader` (task-driven retrieval from the hub bundle) and `okf-writer` (bounded maintenance of hub records): they produce records, never rulings — no gate verdicts, no `src/` writes, no state-counter writes, no commits. The Lead is the sole invoker of both services.

**P2. One accountable owner.** The Lead owns every research deliverable. Advisor feedback does not transfer implementation responsibility.

**P3. Host-agent orchestration, dynamic dual-loop lifecycle.** The Research Lead host prompt defines a non-deterministic research cycle — PLANNING → IMPLEMENTATION → EVALUATION → ANALYSIS — with a bounded inner loop (IMPLEMENTATION ⇄ EVALUATION), a bounded outer loop (plan-cycle → ANALYSIS → revised plan-cycle), mandatory Advisor reviews at loop exits and gates, and explicit termination conditions. It uses `pi-subagents` to invoke the Advisor directly. These are role/prompt-level obligations, not application-enforced workflow gates; a separate Pi permission/policy extension would be needed for non-bypassable enforcement.

**P4. Evidence over agreement.** Advisor endorsement is not proof of correctness. Tests, source verification, experimental observations, and reproducibility determine whether claims are supportable.

**P5. Uncertainty-aware consultation.** The Lead assesses understanding and readiness before meaningful work. Unresolved uncertainty triggers Advisor consultation.

**P6. Mandatory independent review.** PLAN_GATE, INNER_EXIT_GATE, CYCLE_GATE, and REPORT_GATE each require an Advisor verdict, even when the Lead reports high confidence. Individual inner-loop iterations use per-attempt checks plus targeted consultation on triggers; they do not each require a gate review. Verdict/route/next-state combinations follow the authoritative table in §8.4.

**P7. High-information consultation.** Advisor interactions use focused questions, decision-oriented briefs, and references to primary evidence rather than complete conversation histories.

**P8. Research integrity.** Negative results, unresolved questions, failed experiments, and contradictory observations must be preserved and reported.

**P9. Durable execution via git checkpoints.** The Research Lead maintains project artifacts, decisions, and checkpoints in the research workspace so work can resume in a new or recovered host session — and checkpoints mean git commits, not unsaved working-tree state. Commit at every gate decision, cycle boundary, and accepted Worker delivery, with messages naming the gate, verdict, and cycle (e.g. `CYCLE_GATE approve/replan cycle 2, manifest-v3`). Never rewrite published history; versioned artifacts plus manifest hashes make each commit independently auditable. Advisor subagent run/session records provide consultation traceability, but Pi runtime artifacts are not the long-term research source of truth and their retention is configuration-dependent.

**P10. Resource-aware autonomy with human-held stop authority.** Every research project operates within explicit budgets for computation, model usage, iteration, and external actions, tracked by the Lead in project state. Monitoring is the director's prerogative: the human research director watches expenditure with their own tools and alone decides to cease the research. On exhaustion the Lead HOLDs, reports consumption honestly, and awaits the human decision — it neither terminates the program unilaterally nor continues past a spent budget on its own authority.

---

## 2. Architectural decomposition

The target has three role definitions and one host/subagents split:

1. **Research Lead host prompt:** `.pi/agents/research-lead/agent.md`, appended to the main Pi session at startup.
2. **Research Advisor subagent:** `.pi/agents/research-advisor/agent.md`, discovered and invoked through `pi-subagents`.
3. **Engineering Worker subagent:** `.pi/agents/engineering-worker/agent.md`, discovered and invoked through `pi-subagents` for bounded implementation work.

The Lead uses the Pi host's normal tools for research and may implement directly, but delegates bounded implementation work packages to the Engineering Worker and invokes the Advisor with the `subagent` tool for uncertainty-driven consultation and mandatory stage review. No separate workflow script, workflow engine, or fourth agent role is part of the initial target.

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

The initial target consists of three files under `.pi/agents/` and the existing Pi Subagents extension:

```text
.pi/
├── agents/
│   ├── research-lead/
│   │   └── agent.md       # host instructions; appended to main Pi context
│   ├── research-advisor/
│   │   └── agent.md       # Pi subagent definition with frontmatter + prompt
│   └── engineering-worker/
│       └── agent.md       # Pi subagent definition with frontmatter + prompt
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

The host stays actively aware of every child run it launches — silent stalls are a first-class failure mode. After each dispatch the Lead confirms launch success promptly (status check against the recorded run ID), polls bounded background runs instead of assuming completion, and reconciles run/session artifacts on host resume. Any child failure (launch rejection such as an unresolvable model, mid-run error, timeout, missing result) is captured with its error text, recorded in project state, and surfaced to the human in-session immediately — HOLD plus direct notification, never silent retry beyond the capped rounds. Before any real research run, smoke-test all five child definitions with a trivial task so unresolvable models or discovery breaks surface when the fix is cheap.

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

The Advisor's subagent definition must have a strict read-only tool allowlist and no `write`, `edit`, or general-purpose shell access. The Worker's subagent definition must have a bounded write-capable allowlist (read/inspect tools plus `edit`, `write`, and scoped command execution for assigned paths and tests), the `implementation-workflow` and `problem-framing-and-autonomous-decision-making` skills, and a bounded nested-delegation grant (`allowNestedSubagents: true` capped by `maxSubagentDepth: 2`) so it can decompose major packages as the skill directs — never unrestricted fan-out, and never delegation to the Lead role. Direct Worker→Advisor consults are permitted but wasteful: they bypass the Lead's consultation plan and can never produce a gate verdict (verdicts are Lead-requested and manifest-bound only). The host Research Lead has the tools needed to execute the research cycle and the `subagent` tool for Advisor and Worker delegation. Pi tool allowlists narrow Pi tools but do not themselves provide operating-system isolation.

---

## 3. Research Lead specification

### 3.1 Primary capabilities

The Lead requires competence in six areas.

**Research framing**

Convert an open-ended research direction into precise questions, hypotheses, experimental objectives, success criteria, and bounded work packages.

**Technical investigation**

Search, retrieve, compare, and synthesize scientific papers, technical documentation, repositories, benchmarks, and existing implementations.

**Software engineering**

Specify bounded implementation work packages (scope, target paths, acceptance criteria, verification commands), delegate them to the Engineering Worker where parallel or isolated execution helps, and verify the returned evidence. The Lead — not the Worker — decides whether the implementation satisfies the methodology and accepts it into the project.

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

**Verdicts do not route by themselves.** The Lead selects the route from the verdict plus the termination check, using only the legal combinations in the authoritative transition table (§8.4): `approve` enables the gate's forward route; `revise` returns to a named remediation state with a bounded re-review (default max 2 revise rounds per gate, then HOLD and escalate); `inconclusive` permits bounded evidence gathering plus one re-review, then HOLD if still unresolved — never a direct terminal stop; `block` pauses work into HOLD for triage, and only a confirmed-unresolvable blocker (or human decision) converts HOLD into terminal SUSPENDED.

**Fail-closed validation.** The Lead must validate every gate response before acting on it: parseable against the schema above, `gate` matching the gate actually invoked, and `review_target` matching the submitted manifest version. Any failure — malformed output, missing verdict, wrong gate, stale manifest — is a no-verdict: the Lead records it, issues a bounded re-request (default max 2), and HOLDs the gate; if re-requests are exhausted or the Advisor is unavailable, the Lead HOLDs and escalates to the human. Silence, an expired run, or a `complete` run status is never approval. A verdict is invalidated by any later implementation change to the files it covered; per-attempt checks re-validate, and interface/contract-level changes require a fresh gate review.

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
  PLANNING ----------> PLAN_GATE (Advisor review)
     |
     v
  +---------------- OUTER CYCLE n (plan v_n) ----------------+
  |  1. IMPLEMENTATION ⇄ EVALUATION   (inner loop)          |
  |     iterate to best achievable outcome under plan v_n   |
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
  |     +-- blocker / budget spent / early stagnation ------>|
  |             HOLD triage -> SUSPENDED + status report    |
  +----------------------------------------------------------+
```

Two deliberately different pauses: **HOLD** is resumable (awaiting evidence, a bounded re-review, Worker rework, or a human decision); **SUSPENDED** is terminal and always produces a preserved-evidence status report — distinct from an approved final research report, which only COMPLETED produces.

**Three check levels — do not confuse them.** (1) *Per-attempt checks* (tests, smoke evaluations) run inside the inner loop after every implementation change; they decide retry vs. exit, never approval. (2) *Implementation readiness* is the PLAN_GATE `approve` verdict covering plan v_n's implementation baseline; per-attempt fixes stay covered by it unless they touch the interfaces, contracts, or validity assumptions the approval rested on — such changes invalidate the approval and require a fresh PLAN_GATE review before full evaluation. (3) *INNER_EXIT_GATE* is the mandatory Advisor review that closes the inner loop. It admits two package kinds: a complete evidence package, or an explicitly incomplete/invalid package submitted **for diagnosis only** (attempt budget spent, or the fix would require a plan change). A diagnosis-only package may route to ANALYSIS; it may never support a success claim or a `report` route.

**Inner loop — IMPLEMENTATION ⇄ EVALUATION.** Commits endeavor to achieve the best outcome under the current approved plan (plan v_n): build/fix, run smoke tests and evaluations, diagnose failures, and iterate. The Lead executes small or plan-sensitive changes itself and delegates bounded work packages to the Engineering Worker (scoped spec, explicit file paths, acceptance criteria, verification commands); every Worker result returns as observed evidence the Lead verifies before acceptance — and no Worker package may be dispatched until the Lead records READY for it (§8.3). The loop stays inside the plan; it does not change research questions, hypotheses, metrics, or validity criteria. A fix that requires changing the plan (new hypothesis, different baselines/metrics, relaxed success criteria) exits early to ANALYSIS with the evidence marked incomplete-for-diagnosis, instead of silently redefining success inside the loop.

**Outer loop — [PLANNING → IMPLEMENTATION → EVALUATION] → ANALYSIS → [PLANNING → IMPLEMENTATION → EVALUATION].** Commits endeavor to improve or resolve limitations of the initial plan: each outer cycle (n = 1, 2, …) runs the current plan through implementation and evaluation, then ANALYSIS diagnoses what limited the outcome (method, baselines, data, metrics, scope, assumptions) and proposes plan v_{n+1}. Re-planning requires an explicit cycle decision plus Advisor review; the Lead must not start the next outer cycle on its own authority.

**Termination conditions (checked at every ANALYSIS gate, and immediately when discovered):**

1. **Objective achieved** — the approved success criteria are met with valid evidence and Advisor concurrence → enter REPORTING, then COMPLETED.
2. **Unsolvable blocker** — a fundamental methodological, safety, resource, or validity problem with no responsible workaround (Advisor `block` verdict the Lead cannot remediate, missing authority/data, invalidated core assumption) → HOLD immediately for triage (preserve evidence, ask the human where human authority could unblock); convert to SUSPENDED with an honest status report only when confirmed unresolvable or the human so decides. Never downgrade a blocker into an implicit success.
3. **Stagnation despite committed effort** — significant effort has been committed without noticeable positive progress. Quantification: a per-project outer-cycle budget of **3 to 5 outer cycles** (default 4, set in the research charter; the human may override within [3, 5]). Each ANALYSIS records a progress verdict (`advanced | marginal | stalled | regressed`) with evidence. Precedence at CYCLE_GATE: check validated objective achievement **first** — a met objective reports even on the final allowed cycle; only then apply the cap. The cap prohibits authorizing cycle N+1 even when progress is `advanced`. Early stop: 2 consecutive `stalled`/`regressed` cycles with no credible new lever (charter-adjustable, default 2) also ends looping. Any stop for stagnation lands in SUSPENDED with the best-supported conclusion preserved (including inconclusive) — never extra cycles to manufacture a positive result.

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
    |       -> exit inner loop -> ANALYSIS + Advisor cycle review
    +-- fix stays within plan v_n -> next IMPLEMENTATION iteration
    +-- fix requires plan change -> exit to ANALYSIS (no silent redefinition)

ANALYSIS + CYCLE_GATE review (Advisor: interpretation + limitation
    diagnosis + progress verdict + route; see §8.4 table)
    |
    +-- approve + objective met -> REPORTING (REPORT_GATE)
    +-- revise -> bounded remediation in named state -> re-review
    |       (default max 2 revise rounds per gate, then HOLD + escalate)
    +-- replan route approved + outer budget remains -> PLAN_GATE for v_n+1
    +-- inconclusive -> bounded evidence gathering + one re-review,
    |       then HOLD if still unresolved
    +-- block / newly discovered blocker -> HOLD triage immediately;
    |       SUSPENDED + status report only if confirmed unresolvable
    +-- outer cap reached without objective / early-stagnation rule fired
            -> SUSPENDED + status report (best-supported conclusion)
```

**Loop accounting (mandatory project state).** The Lead tracks `outer_cycle` (current plan version n), `inner_attempt` (iteration count within the cycle), per-cycle progress verdicts, Advisor verdicts at each gate, and the remaining outer-cycle budget. Inner-loop iterations do not increment the outer counter; only a CYCLE_GATE-authorized replan starts cycle n+1. **Charging rules:** an outer cycle is charged when the replan is authorized — a plan gate that then fails still consumes the authorized cycle (no free retries); an inner attempt is charged when implementation changes are integrated into the cycle workspace, even if evaluation never completes (no-change interruptions are logged, not charged). Gate revise rounds (default max 2 per gate) and consultation retries (default max 2 per gate) have their own counters and never consume loop budget. Cycle and attempt limits are set in the charter and tracked in `project-state.json` (see 8.4–8.5).

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

**Gate:** The plan and evaluation protocol must be approved before substantial implementation begins.

Where practical, record the experiment protocol before observing the primary evaluation results. Later exploratory modifications must be distinguishable from preregistered tests.

### 5.3 Stage 2 — Implementation

**Objective:** Build the software and experimental infrastructure required by the approved methodology.

The Lead decomposes the approved methodology into bounded work packages and assigns them to the Engineering Worker (or implements plan-sensitive pieces itself). A package states the exact scope, allowed file paths, relevant specs, acceptance criteria, and the verification commands the Worker must run. The Worker edits only granted paths, never project plans (except its own granted plan file under `.pi/plans/`, whose internal progress records it maintains itself), decisions, or review records. Record-keeping split: the Worker owns its skill-plan records; the Lead owns all assignment, acceptance, and project-state records and derives them from the Worker's reported result, never from Worker-written state. The Lead inspects the returned evidence (files changed, test commands with observed results), re-runs key checks where cheap, and accepts or rejects the work; acceptance is a Lead decision, never a Worker claim.

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

**Gate (PLAN_GATE readiness):** Relevant tests must pass and the Advisor must approve the implementation baseline as ready for the planned evaluation. This approval covers the baseline only: later per-attempt fixes stay covered unless they touch the interfaces, contracts, or validity assumptions the approval rested on, in which case the approval is invalid and a fresh PLAN_GATE review is required before full evaluation (see §8.4).

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
5. Propose the cycle decision: `report | replan | hold | suspended`, including plan v_{n+1} changes if re-planning (hypothesis/method/metric/scope deltas and why they should break the limitation). Charter-level objectives and success criteria are out of scope for re-planning: changing them requires explicit human authorization, not a CYCLE_GATE verdict.
6. Check the termination conditions: objective met → `report` route; unsolvable blocker → HOLD triage, SUSPENDED only if confirmed; outer-cycle budget spent without objective met (or consecutive `stalled`/`regressed` cycles with no credible new lever) → SUSPENDED with honest best-supported conclusion. Precedence and charging follow §5.1/§8.4.
7. Record the decision, rationale, and evidence in `cycle-decision.json` before acting on it.

**Required artifacts**

- Evidence-to-hypothesis assessment.
- Threats-to-validity analysis.
- Limitation diagnosis for plan v_n.
- Progress verdict with supporting evidence.
- `cycle-decision.json` (`report | replan | hold | suspended`, rationale, artifact/evidence refs, next-plan deltas if any).

**Advisor review questions**

- Do the findings actually support the stated conclusions, or do they exceed the evidence?
- Could the effects be explained by confounding variables or alternative mechanisms?
- Is the diagnosed limitation actually the binding one, or a symptom?
- Would the proposed plan v_{n+1} plausibly resolve it, or just relabel it?
- Is the progress verdict honest given the metric deltas?
- Has a termination condition fired (objective achieved / unsolvable blocker / stagnation)?

**Gate:** No new outer cycle starts and no REPORTING begins without an Advisor-reviewed cycle decision: the Advisor must concur on (or correct) the interpretation, the limitation diagnosis, the progress verdict, and the route (legal verdict/route combinations in §8.4). `block`/`inconclusive` verdicts, unresolved critical findings, or a spent outer-cycle budget produce HOLD triage, never a new cycle. A `replan` approval authorizes cycle n+1 under the recorded plan deltas; the next cycle's PLAN gate then approves the revised protocol before implementation resumes.

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

`change-and-progress-logs/` is the centralized governance hub of the research project: charter, planning, reviews, and decisions live nowhere else, and `index.md` is the master table the Lead maintains (one row per charter version, plan version, review verdict, decision, and cycle, each pointing at its artifact) so any state — past or present — is retrievable for audits, session resumption, and REPORT_GATE confirmation evidence. The hub is an OKF v0.2 bundle: the Lead tasks `okf-writer` with all concept-record, index, and log writes (with `validate_okf.py` bundle-check before publication) and tasks `okf-reader` with evidence retrieval; the Lead keeps direct ownership of `project-state.json` counters and git checkpoints.

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
- Worker assignments and their structured results (scope, files changed, observed test evidence, acceptance decision), including relevant Pi child run IDs.
- Human decisions, unresolved findings, and project completion status.

The Lead maintains this record. Stage approval refers to an immutable/versioned deliverable manifest; distinguish submitted artifacts from approved artifacts. A task is complete only when its acceptance criteria and verification evidence are recorded. An Advisor child run marked `complete` means only that the consultation settled; it does not mean the research is scientifically valid or accepted. A Worker run marked `complete` means only that the assignment settled; acceptance is recorded separately by the Lead (§8.3).

### 8.2 Advisor consultation and stage review

The Lead performs a structured readiness assessment for each meaningful task and records the conclusion and evidence in the project state. It investigates bounded factual/technical uncertainty directly, consults the Advisor for material conceptual or methodological uncertainty, and pauses for human input when authority or essential information is missing.

Launch the Advisor directly through Pi Subagents with a focused task and fresh context. For example, the host can call `subagent` with `agent: "research-advisor"`, the consultation/review brief as `task`, and `options.context: "fresh"`. The Advisor receives the brief and its own allowed tools; it does not automatically inherit the host's conversation or system prompt. Supply artifact paths/IDs and ask it to inspect primary evidence. If a call runs in the background, the Lead must collect and inspect the completed result before relying on it.

Use the Section 4.4 decision contract for gate reviews. Where appropriate, request Pi structured output with a matching schema and validate the verdict, gate name, and `review_target` manifest version as §4.4 requires; fail closed on any mismatch. A valid schema or successful child run proves only response shape/run completion—not that the claims are true. Record the consultation result in project decisions/reviews before proceeding. If the Advisor is unavailable (no run, error, or re-request budget exhausted), the gate HOLDs and the Lead escalates to the human — unavailability never counts as approval and never advances a gate.

### 8.3 Worker assignment and acceptance

No Worker package may be dispatched until the Lead records READY for it: scope expressible, target paths known, acceptance criteria and verification commands specified. INVESTIGATE/CONSULT/BLOCKED readiness outcomes loop back through reassessment — advisory guidance never substitutes for the gate rubric, and an underspecified package is never dispatched to "let the Worker figure it out."

The Lead assigns each implementation package as a versioned assignment record:

```yaml
assignment:
  assignment_id: "WORK-014"
  base_revision: "git-sha or workspace snapshot the package applies to"
  scope: "exact deliverable; out-of-scope exclusions"
  allowed_paths: ["paths the Worker may read", "paths the Worker may modify"]
  governing_specs: ["spec/artifact-ids the implementation must satisfy"]
  acceptance_criteria: ["checkable criteria"]
  authorized_verification: ["exact commands the Worker may run"]
  attempt_budget: "max integration attempts for this package"
  deadline: "soft stop (return PARTIAL) + hard cutoff (host-handled, §8.5)"
```

Launch the Worker through Pi Subagents with `agent: "engineering-worker"`, the package as `task`, and a fresh context; the Worker inherits project context as configured but never the Lead's live reasoning. It edits only granted paths — never plans, decisions, reviews, or state records — and returns a structured result echoing the `assignment_id`:

- `SUCCESS`: changed artifacts (paths + versions/hashes), every authorized verification command with observed output verbatim (or explicit `not-run` with reason), deviations from the package, remaining follow-ups.
- `PARTIAL`: what is done and verified, exact state of the rest, what was not attempted.
- `BLOCKED`: the blocking fact, what was tried, the smallest unblock needed (corrected scope, missing spec, environment fix, or plan-level question).

A missing, malformed, or timed-out result is a host-handled no-result: reconcile the workspace against `base_revision` before retrying or reassigning, and never treat dispatch or a `complete` run status as evidence. The Lead inspects the result, re-runs key verification where cheap, and records `accepted` or `rejected` with rationale before the output enters the evidence base; acceptance is a Lead decision, never a Worker claim. Never silently broaden a Worker's scope to fix a failure: re-scope explicitly, or route plan-level changes through ANALYSIS.

**Worker-blocker triage.** A `BLOCKED` (or rejected) result routes by cause, not by default:

| Cause | Route |
|---|---|
| Package underspecified or wrong scope/paths | Lead corrects and re-issues the package (new attempt against the package budget) |
| Environment/tooling failure | Lead fixes or works around; HOLD the package if human credentials or quota are needed |
| Technical approach uncertain within the plan | Targeted Advisor consultation, then reassess readiness |
| Fix would change the plan | ANALYSIS via INNER_EXIT_GATE (diagnosis-only package); no silent redefinition |
| Repeated BLOCKED against the package budget | HOLD + escalate to human (see §8.4 revise-round limits) |

### 8.4 Loop-aware progression and host-session resumption

The Research Lead follows a loop-aware progression, not a linear stage chain. Outer-cycle count, inner-attempt count, progress verdicts, and termination status are first-class project state. This table is authoritative for every gate: if prose elsewhere suggests a different next step, this table governs.

```text
CREATED -> SCOPING -> PLANNING -> PLAN_GATE (plan v_n approved?)
        -> [ INNER LOOP: IMPLEMENTING ⇄ EVALUATING ]
             (inner_attempt = 1, 2, ... under plan v_n)
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
| PLAN_GATE | `approve` | `continue` → inner loop under plan v_n |
| PLAN_GATE | `revise` | `remediate-plan` → PLANNING, then re-review (max 2 rounds, then HOLD + escalate) |
| PLAN_GATE | `inconclusive` | `gather-evidence` → bounded evidence + one re-review, then HOLD if unresolved |
| PLAN_GATE | `block` | HOLD triage immediately; SUSPENDED + status report only if confirmed unresolvable |
| INNER_EXIT_GATE | `approve` (complete package) | `continue` → ANALYSIS |
| INNER_EXIT_GATE | `approve` (diagnosis-only package) | `continue-to-diagnose` → ANALYSIS; package is barred from supporting success claims |
| INNER_EXIT_GATE | `revise` | `remediate-implementation` → bounded inner-loop rework, then re-review (max 2 rounds, then HOLD + escalate) |
| INNER_EXIT_GATE | `inconclusive` | `gather-evidence` → bounded evidence + one re-review, then HOLD if unresolved |
| INNER_EXIT_GATE | `block` | HOLD triage immediately |
| CYCLE_GATE | `approve` + objective met | `report` → REPORTING |
| CYCLE_GATE | `approve`/`revise` + objective unmet, replan justified, budget remains | `replan` → PLAN_GATE for v_n+1 (charges the new cycle) |
| CYCLE_GATE | `revise`, fix stays within plan | `remediate-implementation` → bounded inner-loop rework, then INNER_EXIT_GATE re-review |
| CYCLE_GATE | `inconclusive` | `gather-evidence` → bounded evidence + one re-review, then HOLD if unresolved |
| CYCLE_GATE | `block`, or cap reached, or early-stagnation rule fired | HOLD triage → SUSPENDED + status report (SUSPENDED is terminal; HOLD needs a human decision to resume or convert) |
| REPORT_GATE | `approve` | `complete` → COMPLETED (final research report: executive summary, read alone, preserves the main limitation, decision-relevant negatives, and the action boundary; Advisor confirms consistency with evidence) |
| REPORT_GATE | `revise` | `remediate-report` → REPORTING, then re-review (max 2 rounds, then HOLD + escalate) |
| REPORT_GATE | `inconclusive` | `gather-evidence` → bounded evidence + one re-review, then HOLD if unresolved |
| REPORT_GATE | `block` | HOLD triage immediately; SUSPENDED + status report only if confirmed unresolvable |
| Any gate | no-verdict (invalid output, stale manifest, unavailable Advisor) | HOLD + bounded re-request (max 2), then escalate to human |

A `replan` route increments `outer_cycle` and resets `inner_attempt`; inner iterations never increment the outer counter. Inner-attempt exhaustion does not stop the project by itself: it forces INNER_EXIT_GATE with the package marked incomplete-for-diagnosis, so ANALYSIS can diagnose the failure instead of being starved of it. The Lead's instructions and project state define this policy; Pi does not automatically prevent the host model from skipping a step. Resumption uses the project state (including loop counters, HOLD/SUSPENDED status, and the latest `cycle-decision.json`) and artifact manifest, then checks the prior Advisor review/run evidence before continuing. If state and evidence disagree, stop and reconcile rather than infer approval.

**Termination enforcement.** The charter sets `max_outer_cycles` (integer in [3, 5], default 4; human-adjustable within range). The Lead checks the three termination conditions at every CYCLE_GATE and immediately when a blocker surfaces: (1) validated objective achievement → `report` route (checked first, even on the final allowed cycle); (2) unsolvable blocker → HOLD triage, then SUSPENDED with full evidence preservation and a status report if confirmed; (3) stagnation — outer cap reached without the objective met, or the early-stagnation rule (default 2 consecutive `stalled`/`regressed` cycles with no credible new lever, charter-adjustable) → SUSPENDED with the best-supported (possibly inconclusive) conclusion. A SUSPENDED stop produces a status report (what was tried, what failed, preserved evidence); it never produces an approved final research report. No instruction may force a positive conclusion or an extra cycle once termination has fired.

Pi run/session state helps recover Advisor consultations and inspect their results, but the host Research Lead's conversational state is not a durable workflow engine. A new host session reloads the prompt file, reads the project state, and resumes explicitly. Do not claim automatic transactionality or indefinite recovery for the whole research cycle.

### 8.5 Bounded autonomy and budgets

Use explicit project-level limits for:

- Outer cycles: `max_outer_cycles` in [3, 5] (default 4), recorded in the charter; inner attempts per cycle (bounded, e.g. set per project).
- Gate revise rounds (default max 2 per gate) and consultation/evidence retries (default max 2 per gate): tracked separately, never charged against loop budgets.
- Advisor consultations and repeated reviews.
- Worker packages: per-package attempt budget plus two deadlines — a soft stop (Worker wraps up, runs verification on what is done, returns PARTIAL) and a hard cutoff (host-handled timeout: treated as no-result per §8.3, never dependent on a final Worker response).
- Experiment runs and wall-clock duration.
- Model token/cost usage and external API expenditure.
- Sandbox CPU, memory, storage, and network use.

The Research Lead tracks these limits in project state. Pi Subagents can report child-run usage and accept per-run controls, but such controls do not replace external compute/API quotas or guarantee stopping all already-running work at a budget boundary. A hard tool budget can block needed operations, and deadline termination can interrupt a mutation. Prefer narrow tasks, explicit checkpoints, external resource quotas, and project-level accounting.

When a limit is reached, stop advancing and report completed work, unresolved issues, consumed resources, and the next decision. No instruction should force a positive research conclusion when evidence is insufficient.

### 8.6 Director communication contract

The human research director governs; the Lead keeps them governable. The director should be able to tell in one read what changed, why it matters, whether they must act, and what the Lead will do next. Upward communication has a fixed shape, not ad-hoc prose:

- **Standing brief (a dated view, not a second ledger).** `change-and-progress-logs/director-brief.md` is the executive summary: objective status, cycle/progress, spend-vs-budget, blockers, pending decisions. Refresh at every CYCLE_GATE and REPORT_GATE, and also on any new/closed/superseded director decision, material change in run status or research conclusion, or budget hold. Start with as-of timestamp and current stage, then what changed and why it matters, decision needed or none, next checkpoint. Link to state, evidence, and decisions instead of duplicating them. For spend, show source, timestamp, and coverage; distinguish recorded spend, estimates, and unknown external charges — the director's own tools remain the monitoring channel. At kickoff, ask what should interrupt them and what tradeoff to prioritize on borderline evidence; revisit after the first consequential decision or on feedback ("too late", "too much detail"). Preferences change delivery only — never the charter, never escalation. Never promise timed check-ins or monitoring while the host is inactive unless demonstrated.
- **Tag by who must act, not by lifecycle state.** `DECISION-REQUIRED` when authority or essential information must come from the director — the run parks with no dependent progression until decided. `FYI` when the Lead owns the next action, even for a serious incident (“evaluation paused; reconciling the workspace, will retry within the existing cap — no action needed”). Record the fault either way. A HOLD for evidence, re-review, rework, or bounded re-request is FYI unless it needs the director; a HOLD at an authority boundary (charter change, budget exhaustion, unresolvable blocker, no credible lever) is DECISION-REQUIRED. Escalate on real authority boundaries or exhausted recovery, never merely on the first error.
- **Decision requests that are easy to answer.** Put the ask in the first sentence: why now, the viable options with consequences, the Lead's recommendation and what would change it, what happens without a reply. Deadlines only for real cutoffs; otherwise “before the next run.” One decision ID shared across chat, indexed record, and brief.
- **Close the loop.** Distinguish questions and preferences from authorization. Ambiguous reply → one focused question, never guess; clear reply → act, no ceremonial reconfirmation. Read back the effect, not the transcript (“D-014 recorded: narrow to X; Y out of scope; revising plan for PLAN_GATE before implementation”). Close or supersede the open entry and refresh the brief. If posting or recording fails, disclose the gap when possible and reconcile by ID on resume — never infer receipt or approval. A stop order is honored before polishing records; distinguish work told to stop from work confirmed stopped.
- **Durable and in-session.** Every DECISION-REQUIRED message is recorded in the hub (`decisions/`, indexed in `index.md`) AND surfaced to the human in-session immediately. In-session alone evaporates; records alone go unread — both are mandatory.
- **Director questions.** Answer from the freshest records and name discrepancies (“the brief predates the timeout; state shows evaluation paused; confirmation not yet recorded”). Say explicitly when the answer is not recorded — never improvise.
- **Final report audience.** Written for two readers: executive summary for the director (what was found, what it means, what remains open) over a technical body for the record. REPORT_GATE confirms the summary, read alone, preserves the main limitation, decision-relevant negatives, and the boundary on what the director should do with the finding.

**SUSPENDED conversion authority.** Reaching the charter's cycle cap or firing the early-stagnation rule converts to SUSPENDED by the Lead (charter-mandated, mechanical) with a report; a confirmed-unresolvable blocker converts by the Lead after triage with evidence preserved. Cease, narrow, or resume-with-more-budget decisions convert only by the human director — the Lead HOLDs, reports, and awaits. Budget exhaustion alone never converts without a human decision.

### 8.7 Knowledge-service delegation

The Lead delegates documentation mechanics to the two knowledge services (§2.4) and keeps judgment, state, and checkpoints. Standing rules:

- **Reader for evidence assembly.** Task `okf-reader` with pre-gate evidence gathering (“minimum sufficient evidence for CYCLE_GATE on X”) and mid-run director questions. Its RESULT.md JSON carries the searched scope — never treat a no-match as absence beyond that scope. Gaps are Lead investigation tasks, not stoppers-by-default and never silent skips at gates.
- **Writer for record mechanics.** Task `okf-writer` with decision records, brief-refresh mechanics, index/log updates, and review-record filing, stating exact intended changes and scope. On `committed`, spot-check before gate reliance; on `needs_review`/`rejected`, triage (supply evidence, narrow scope, or record the conflict) — never silently override or fabricate missing metadata. The writer never commits; git checkpoints stay the Lead's.
- **Content stays the Lead's.** The services shape records; judgments (brief assessments, decision rationale, verdict intake, acceptance) originate with the Lead and pass through the writer as content, not as service inference.

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

**Use the main Pi session as the Research Lead host, and use `pi-subagents` to launch the Research Advisor and the Engineering Worker as children.** The initial implementation consists of three files under `.pi/agents/`; it does not include a separate workflow script, a Research Lead child agent, or another agent framework.

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

The Lead prompt is not a child agent and should not be launched with `subagent`. Prefer plain Markdown without Pi subagent YAML frontmatter for this file; only the Advisor and Worker files need subagent frontmatter. If the Lead file is nevertheless discovered as a child, exclude `agents/research-lead` from `subagents.agentExcludeDirs` in `.pi/settings.json` (relative to `.pi`); this removes it from the child catalog without affecting direct `--append-system-prompt` loading. Keep only `research-advisor` and `engineering-worker` available as the research subagents. Note the current project `.pi/settings.json` is empty (`{}`): the exclusion, model overrides, and any tool defaults must still be added and their effect verified — list the discovered child catalog before and after, and confirm the Lead prompt loads via the flag in both states.

**Runtime pin and verification checklist.** This design was written against Pi CLI 1.6.0 and `pi-subagents` 0.89.2. Before implementing the prompts, pin the deployed versions and verify each of the following against the running system; every frontmatter field and invocation below is conditional on verification until then:

1. The exact frontmatter keys the deployed `pi-subagents` honors (`tools`, `model`, `thinking`, `systemPromptMode`, `inheritProjectContext`, `defaultContext`, `acceptanceRole`, aliases) — the reference file's keys are examples, not proof.
2. What a fresh child context excludes (host conversation, host system prompt) and still loads (project context files, skills, tool providers) for each child.
3. The effective tool list of each child at launch (inspect, don't assume), including that no delegation-capable tool is reachable from the Advisor child, and that the Worker child's only delegation path is the bounded `allowNestedSubagents` grant capped at depth 1.
4. The `agentExcludeDirs` path base and its effect on discovery vs. direct prompt loading.
5. Structured-output support and schema-constraint behavior for gate verdicts (§4.4, §11.2–11.3).

The Research Lead's tools come from the main Pi host configuration. Ensure the `pi-subagents` extension and its `subagent` tool are available in that session. The Advisor's frontmatter should set an explicit read-only tool allowlist (for example `read`, `grep`, `find`, `ls`, plus selected read-only evidence providers), project-context inheritance as needed, a separately configurable model, and no nested subagent delegation. The Worker's frontmatter should set a bounded write-capable allowlist (read/inspect tools plus `edit`, `write`, and scoped command execution such as `bash`/`codemode` for assigned paths and tests), the `implementation-workflow` and `problem-framing-and-autonomous-decision-making` skills, a bounded nested-delegation grant (`allowNestedSubagents: true`, `maxSubagentDepth: 2`), and a separately configurable model. Loading a tool provider/extension and allowlisting its tool are separate configuration steps.

### 10.3 Host-led Advisor delegation

For a consultation or mandatory stage review, the Lead calls `subagent` directly with `agent: "research-advisor"` and a focused `task` containing the decision/review brief, rubric, constraints, and exact artifact paths/IDs. Use a verified fresh child context (see §10.2 checklist: excludes host conversation and host system prompt; inherits only configured project context) so the Advisor assesses the supplied evidence rather than inheriting the Lead's conversation. Where appropriate, request schema-constrained structured output matching Section 4.4 and validate the returned verdict, gate name, and `review_target` before proceeding.

The Lead owns all stage sequencing, task execution, remediation, project-state updates, and direct human escalation. It should invoke one Advisor child per decision/review, consume the result via the Pi subagent result/status mechanism, and preserve useful outcomes in project files. Use asynchronous child execution for long consultations when it keeps the host responsive, but do not treat dispatch acceptance as a completed review.

### 10.4 Host-led Worker delegation

For implementation work, the Lead calls `subagent` with `agent: "engineering-worker"` and a focused `task` containing the work package: exact scope, allowed file paths, governing specs, acceptance criteria, verification commands, and the attempt/deadline budget. Use a fresh child context so the Worker implements from the package rather than inheriting the Lead's exploratory reasoning. Prefer one Worker child per work package. Default to one active Writer per workspace; concurrent packages require isolated workspaces (one worktree per package) plus Lead-controlled integration in recorded order against each package's `base_revision`. Before every dispatch, persist the assignment ID, child run ID, and workspace ref in project state; on host resume, reconcile live runs and unaccepted changes against those refs before retrying, reassigning, or advancing. The Lead must collect each result, inspect files changed and observed verification output (re-running key checks where cheap), and record acceptance before the code enters the evidence base. Never treat Worker dispatch, a `complete` run status, or the Worker's own success claim as acceptance.

Do not add `.pi/workflows/research-lifecycle.js` as a required component in version 1. A reusable `pi-subagents` scripted workflow may be considered later for a well-defined mechanical sequence, but it is not the host's role and must not replace the Research Lead as lifecycle owner.

### 10.5 Suggested initial stack

| Component | Recommendation |
|---|---|
| Host agent | Pi main session with the Research Lead prompt appended at startup |
| Subagent runtime | Pi Subagents extension (`pi-subagents`) |
| Host prompt | `.pi/agents/research-lead/agent.md` |
| Advisor subagent | `.pi/agents/research-advisor/agent.md` |
| Worker subagent | `.pi/agents/engineering-worker/agent.md` |
| Agent discovery | Project `.pi/settings.json`; exclude the Lead prompt directory if it would be discovered as a child |
| Lead model | Main Pi session's configured model; selected by the operator |
| Advisor model | Independently configurable in Advisor frontmatter or `subagents.agentOverrides` |
| Worker model | Independently configurable in Worker frontmatter or `subagents.agentOverrides`; strong enough to write correct code and tests, since flawed output costs Lead verification and rework |
| Source control | Git; use isolated worktrees when concurrent or risky code changes require them |
| Project state and artifacts | Versioned project files plus immutable external artifact storage for large outputs |
| Experiment analysis | Python, pandas, SciPy, and task-specific libraries where appropriate |
| Literature sources | Academic search/publisher APIs, official documentation, and repositories through explicitly loaded tools |
| Verification | Tests, executable checks, source provenance, and independent scientific assessment |
| Observability | Pi Advisor and Worker run/session/usage records plus durable project decision and artifact manifests |

The Lead must be capable enough to implement and evaluate real experiments. A cheaper model that frequently generates flawed work may increase total cost through rework and Advisor consultations.

### 10.6 Tool permissions and security

**Research Lead host**

- Uses the main Pi session's filesystem, repository, terminal, research, and experiment tools within the host's configured permissions.
- Uses the `subagent` tool to delegate bounded consultation/review work to `research-advisor` and bounded implementation work to `engineering-worker`.
- Owns implementation acceptance and project artifact changes.

**Research Advisor subagent**

- Read-only access to artifacts, source, tests, results, and literature relevant to the task.
- Selected read-only retrieval and optional isolated analysis tools.
- No `write`, `edit`, or general-purpose shell access; no nested subagent delegation.

**Engineering Worker subagent**

- Read/inspect tools plus `edit`, `write`, and scoped command execution (`bash`/`codemode`) limited to assigned paths, tests, and verification commands; the `implementation-workflow` and `problem-framing-and-autonomous-decision-making` skills for major-task execution.
- No access to project plans, decisions, reviews, or state records — except the package's own plan file under `.pi/plans/` when the package explicitly grants it; bounded nested delegation only (`allowNestedSubagents`, depth ≤ 2, skill-directed, never to the Lead role; Worker→Advisor calls permitted but wasteful and verdict-less) — no unrestricted fan-out.
- Returns the Section 8.3 structured result for every assignment, including blocked or partial work; reports blockers in the returned result (no heartbeat channel in version 1), never to the human directly.

Apply sandboxing, filesystem/network boundaries, secrets management, resource quotas, restricted external side effects, prompt-injection defenses, and human approval for irreversible or externally visible actions at the host/tool layer. Pi tool allowlists are not an operating-system sandbox. Retrieved pages, repositories, datasets, prompts, and dependencies are untrusted data—not instructions that may override either role contract.

---

## 11. Agent prompts and contracts

### 11.1 Research Lead host-prompt template

**Role:** Autonomous Applied AI Research Lead, running in the main Pi session.

**Loading:** Start the host session with `pi --append-system-prompt .pi/agents/research-lead/agent.md` from the repository root. This file configures the host role; it is not a subagent to launch.

**Mission:** Transform human research directions into rigorous, reproducible research results while owning the full research lifecycle.

**Responsibilities**

- Own research planning, implementation, evaluation, analysis, and reporting.
- Maintain project state, artifacts, evidence, budgets, and decisions in the research workspace.
- Assess task understanding and readiness before substantial work.
- Use the `subagent` tool to consult or independently review with `research-advisor` when required, and to assign bounded implementation packages to `engineering-worker`; do not create or delegate to any other agent roles.
- Verify Worker results against acceptance criteria and re-run key checks where cheap; accept or reject the work explicitly.
- Submit completed artifacts for mandatory Advisor review at every stage gate.
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

Notes: no `subagent` tool (the Worker cannot spawn agents) and no heartbeat/`contact_supervisor` in version 1 — silence is handled by bounded run status plus workspace reconciliation (§8.3, §8.5). Loading a tool provider/extension and allowlisting its tool are separate configuration steps. Frontmatter allowlists state intent; the enforceable boundary is the Milestone 3 confinement verification, not this file.

**Role:** Bounded research implementation worker, invoked as the `engineering-worker` Pi subagent.

**Mission:** Implement exactly the assigned work package — code, tests, configs, reproduction commands — and return complete, honest evidence of what was done and observed.

**Tool and authority boundary**

- Edit only granted code/test/config paths; never touch plans, hypotheses, decisions, reviews, state records, or out-of-scope files.
- Never spawn agents, orchestrate later stages, broaden scope, relax verification, or claim an unrun check passed.
- A `complete` run status reports that the assignment settled; only the Lead's acceptance makes the output project evidence.

**Responsibilities**

- Implement the package per the assigned spec and acceptance criteria.
- Run the assigned verification commands (plus adjacent affected tests) and record observed output verbatim — pass or fail.
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
| Advisor receives insufficient context | Requests primary evidence |
| Advisor gives contradictory advice | Lead records conflict and seeks empirical resolution |
| Experiment returns negative result | Preserve and report honestly |
| Upward message lacks tag or record | Lead tags every message DECISION-REQUIRED or FYI and records the former; untagged escalations are a process failure |
| Director asks mid-run status | Lead answers from the standing brief and indexed records, or states explicitly what is not yet recorded |
| Ambiguous director reply | Lead asks one focused question, never guesses; reads back the recorded effect; closes or supersedes the entry and refreshes the brief |
| Writer returns `needs_review` | Lead triages: supply missing evidence/authorization, narrow scope, or record the conflict — never silently override or fabricate metadata |
| Reader reports gaps | Gaps become investigation tasks; gates never rely on absent evidence |
| Validator reports structural errors | Fix records before gate reliance; a passing validator is form-only, never evidence truth |
| Experiment results are inconsistent | Investigate variability and validity |
| Lead host session or Pi process is interrupted | Start a new host session with the Research Lead prompt, reconcile project state/artifacts, and resume explicitly; recover an Advisor child run only when supported by `pi-subagents`, otherwise relaunch from durable evidence |
| Worker run interrupted after changing files but before acceptance | Treat as no-result: reconcile the workspace against the assignment `base_revision`, quarantine unaccepted changes, re-verify from the recorded revision, then retry or reassign — never accept orphaned mutations |
| Research budget is exhausted | HOLD, report consumption, and ask the human; only the director decides resume (extended budget), narrow, or cease (→ SUSPENDED + status report) |
| Retrieved document contains malicious instructions | Treat as untrusted content |
| Evaluation data is contaminated | Flag the validity threat and stop affected claims |

---

## 13. Implementation roadmap

### Milestone 1 — Research Lead host prompt, Advisor subagent, and Worker subagent

Implement:

- `.pi/agents/research-lead/agent.md`, loaded into the main Pi session with `--append-system-prompt`.
- `.pi/agents/research-advisor/agent.md` as the Pi subagent definition.
- `.pi/agents/engineering-worker/agent.md` as the bounded-writer Pi subagent definition (modeled on `implementation-workflow-worker`).
- Clear tool boundaries: Lead owns execution, acceptance, and decisions; Advisor is read-only and cannot spawn more agents; Worker is restricted by prompt rules to granted paths, assigned verification, observed-evidence returns, and no agent spawning — prompt-level only in this milestone (see confinement note below).
- Project state/artifact layout, the Advisor consultation/review contract, and the Worker assignment/acceptance contract (Section 8.3).
- Agent-discovery exclusion for the Lead prompt directory if its format would otherwise make it a child agent.

**Exit criterion:** The Lead prompt loads in the host session; the Advisor and Worker are discoverable and can be invoked by name; the Advisor returns read-only inspection evidence; the Worker returns structured evidence for granted-path work; the Lead independently routes and consumes consultations and work packages. This exit is behavioral evidence only: nothing in Milestone 1 proves the Worker cannot touch out-of-scope paths — prompt rules are not enforcement. Enforceable confinement (denied out-of-scope read/write/execution/delegation tests, named enforcement point) is verified in Milestone 3 before any write-capable deployment beyond exercises.

### Milestone 2 — Host-led lifecycle discipline

Implement and test through bounded research exercises:

- The dynamic dual-loop sequence (inner IMPLEMENTATION ⇄ EVALUATION, outer plan-cycle → ANALYSIS → re-plan), loop counters, termination conditions, and mandatory Advisor review instructions in the Lead prompt.
- Readiness checks, consultation triggers, fresh-context review packets, and bounded revise/HOLD decisions.
- Project-state updates, immutable artifact manifests, and resume instructions for a new host session.
- Human clarification/escalation behavior and explicit disclosure that gates are host-agent policy, not application-enforced workflow.

**Exit criterion:** The Lead loops through inner/outer cycles with counter tracking, launches the Advisor at all mandatory gates, records verdicts/evidence and per-cycle progress, honors all three termination conditions (including stopping after the outer-cycle budget is spent), and does not proceed after unresolved blockers during acceptance exercises. This is behavioral evidence, not a hard runtime guarantee.

### Milestone 3 — Research execution tools

Implement:

- Trusted literature/search tools and source provenance.
- Repository and project artifact access.
- Isolated code execution, automated testing, and experiment runner.
- Worker confinement verification: denied out-of-scope read/write/execution/delegation probes against the named enforcement point (host/tool-layer sandbox and workspace isolation); read permission verified separately from modify permission. No write-capable Worker deployment beyond exercises until these probes pass.
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

- Tested host-session resumption from durable project state, Advisor-run recovery where supported, and Worker workspace reconciliation (assignment/run/workspace refs, unaccepted-change quarantine per §8.3–§8.4).
- External compute/API quotas and project-level resource accounting.
- Context package generation, selective evidence expansion, and decision reuse.
- Token/cost attribution and measured evaluation of consultation effectiveness.

**Exit criterion:** The system demonstrates measurable improvements in research quality and resource efficiency while preserving honest failure and inconclusive outcomes.

Do not add a lifecycle workflow script, another agent role beyond the three defined, a large memory service, or a dashboard before evaluation demonstrates that need.

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

The Advisor reviews the design and inspects evidence that the implementation matches the experiment protocol.

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

**Stage 4 — Analysis.** The Lead compares observations against the competing causal hypotheses and diagnoses the binding limitation of plan v_1 (e.g. sampling variability and reasoning-token budget confound the causal claim). The Advisor challenges the interpretation — asking whether variation in answer formatting, stochastic sampling, or computational budget explains the observations — and reviews the progress verdict and cycle decision. If the diagnosis calls for a design change the current plan cannot absorb (e.g. new controls or task families), the approved `replan` starts outer cycle 2 under plan v_2; otherwise the Lead iterates the inner loop again if inner-attempt budget remains. The loop repeats until the objective is met, an unsolvable blocker appears, or the outer-cycle budget (3–5 cycles) is spent. Any replan that would change the success criteria or research objective itself requires human authorization first (§9.5) — the Advisor cannot approve charter changes.

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
| Number of role definitions | Three core roles (Lead host prompt, Advisor subagent, Worker subagent) plus three specialist advisors plus two knowledge services (okf-reader, okf-writer); closed set per P1 |
| Research Lead | Main Pi session loaded with `.pi/agents/research-lead/agent.md` via `--append-system-prompt` |
| Research Advisor | Read-only Pi child agent at `.pi/agents/research-advisor/agent.md` |
| Engineering Worker | Bounded-writer Pi child agent at `.pi/agents/engineering-worker/agent.md` (nested delegation bounded: skill-directed, depth ≤ 2) |
| Specialist advisors | Pre-existing read-only consultants (`harness-architector`, `backend-architector`, `frontend-architector`); called by Lead directly or by Worker nested; advise only, never gate/decide/implement |
| Primary owner | Research Lead host agent |
| Orchestration | Research Lead directly invokes `research-advisor` and `engineering-worker` through `pi-subagents` `subagent` tool |
| Agent autonomy | Lead executes research work in the host session; Advisor provides bounded advice/review child runs; Worker executes only assigned implementation packages and returns observed evidence |
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

This revision targets the Pi Subagents API described in the referenced documentation. Pin the deployed extension version and re-check agent discovery, direct delegation, model/tool configuration, and child-run behavior when upgrading it.
