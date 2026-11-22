# System Design Guideline
## Two-Agent Autonomous Research Team for Applied AI: LLM & Agentic Systems

**Version:** 1.0 — Proposed Architecture  
**Primary objective:** Build an autonomous, evidence-driven research system that converts a human-defined research direction into a research roadmap, implemented experiments, evaluated findings, and a rigorous final report.

---

## 1. System objectives and design principles

### 1.1 Mission

The research system operates as a small autonomous research team with two specialized roles:

- **Research Engineer:** The operational owner responsible for planning, investigating, implementing, experimenting, evaluating, analyzing, and reporting.
- **Research Advisor:** The intellectual and methodological reviewer responsible for theoretical guidance, problem clarification, critical assessment, and quality assurance.

The human research director provides research directions, goals, constraints, and feedback when necessary.

The expected workflow is:

```text
Human introduces research direction
                 |
                 v
        Research Engineer
                 |
       Develop research plan
                 |
       Consult Research Advisor
                 |
       Implement experiments
                 |
       Consult Research Advisor
                 |
       Execute and evaluate
                 |
       Consult Research Advisor
                 |
       Analyze and report
                 |
       Consult Research Advisor
                 |
                 v
     Deliver verified research
```

The Engineer should be able to execute the entire research lifecycle without routine human intervention.

Human involvement is reserved for decisions requiring human authority, unavailable information, changes to major research objectives, or unresolved critical issues.

### 1.2 Core principles

**P1. Two agents only.** Do not create additional Planner, Critic, Reviewer, Evaluator, or Writer agents. These are functions of the two established roles.

**P2. One accountable owner.** The Engineer owns every research deliverable. Advisor feedback does not transfer implementation responsibility.

**P3. Deterministic lifecycle, autonomous execution.** The research stages and required review gates are enforced by application code. The Engineer retains autonomy over technical work inside those stages.

**P4. Evidence over agreement.** Advisor endorsement is not proof of correctness. Tests, source verification, experimental observations, and reproducibility determine whether claims are supportable.

**P5. Uncertainty-aware consultation.** The Engineer assesses understanding and readiness before meaningful work. Unresolved uncertainty triggers Advisor consultation.

**P6. Mandatory independent review.** Every completed research stage requires Advisor assessment, even when the Engineer reports high confidence.

**P7. High-information consultation.** Advisor interactions use focused questions, decision-oriented briefs, and references to primary evidence rather than complete conversation histories.

**P8. Research integrity.** Negative results, unresolved questions, failed experiments, and contradictory observations must be preserved and reported.

**P9. Durable execution.** The system must survive interruptions and resume without losing research state, decisions, experimental artifacts, or session references.

**P10. Resource-aware autonomy.** Every research project operates within explicit budgets for computation, model usage, iteration, and external actions.

---

## 2. Architectural decomposition

The system has two LLM-based agents, supported by non-agent infrastructure.

### 2.1 Logical architecture

```text
              HUMAN RESEARCH DIRECTOR
                        |
                        v
              RESEARCH CONTROL PLANE
              ----------------------
              Project / task state
              Workflow state machine
              Budget enforcement
              Review gate enforcement
              Persistence / recovery
                        |
                        v
                RESEARCH ENGINEER
                -----------------
                Planning
                Literature research
                Coding
                Experiment execution
                Evaluation
                Analysis
                Reporting
                        |
                Advisor gateway
                        |
                        v
                 RESEARCH ADVISOR
                 ----------------
                 Theory & principles
                 Research methodology
                 Deep reasoning
                 Critical review
                 Decision guidance
                        |
                        v
                 REVIEW DECISION
                        |
                        v
              WORKFLOW CONTROLLER
                        |
                        v
              Continue / Revise / Stop


    SHARED RESEARCH INFRASTRUCTURE
    --------------------------------
    Git repository and artifacts
    Literature and evidence records
    Experiment runner and datasets
    Persistent research state
    Tracing and evaluation records
```

The workflow controller must not be another autonomous agent.

It should be deterministic software responsible for coordinating the two agents, enforcing policies, and persisting state.

This prevents the controller itself from becoming another source of uncertain autonomous decisions.

### 2.2 Agent separation

| Responsibility | Engineer | Advisor |
|---|---|---|
| Interpret research direction | Owns | Clarifies |
| Define research questions | Owns | Challenges |
| Literature review | Executes | Assesses relevance and coverage |
| Research methodology | Designs | Reviews and improves |
| Research roadmap | Creates | Approves or requests revision |
| Implementation | Executes | Reviews design and evidence |
| Experiment execution | Executes | Challenges validity |
| Statistical analysis | Executes | Reviews interpretation |
| Final report | Writes | Critically reviews |
| Project status | Maintains | Reads as necessary |
| Research decisions | Proposes and implements | Advises and reviews |
| Human escalation | Initiates | Can recommend |
| Budget management | Operates within limits | Uses allocated consultation budget |

The Advisor should not be granted general-purpose implementation authority. This preserves separation of responsibility and keeps the expensive model focused on high-value intellectual work.

---

## 3. Research Engineer specification

### 3.1 Primary capabilities

The Engineer requires competence in six areas.

**Research framing**

Convert an open-ended research direction into precise questions, hypotheses, experimental objectives, success criteria, and bounded work packages.

**Technical investigation**

Search, retrieve, compare, and synthesize scientific papers, technical documentation, repositories, benchmarks, and existing implementations.

**Software engineering**

Implement experiment code, configure environments, run automated tests, debug failures, and manage version-controlled artifacts.

**Experimental methodology**

Construct baselines, identify confounding variables, design controls, run experiments, and collect measurements.

**Scientific analysis**

Interpret quantitative and qualitative findings, test alternative explanations, estimate uncertainty, and distinguish evidence from conjecture.

**Technical reporting**

Produce reproducible research reports connecting questions, methods, observations, results, conclusions, and limitations.

### 3.2 Mandatory task-readiness assessment

Before beginning each meaningful task, the Engineer must execute a readiness check.

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

The Engineer should not assign arbitrary numerical confidence scores as though they were calibrated probabilities.

Confidence must be tied to observable evidence.

For example:

> The algorithm and implementation approach are established, the benchmark and baseline are available, and the output can be verified by deterministic tests. No unresolved methodological concern currently prevents execution.

This is more useful than declaring "confidence: 95%."

### 3.3 Uncertainty classification

The Engineer should distinguish different kinds of uncertainty.

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

However, if the Engineer cannot resolve a material uncertainty through clearly bounded investigation, consultation becomes mandatory.

### 3.4 Mandatory consultation triggers

Consult the Advisor when:

1. The research question cannot be precisely formulated.
2. Critical theoretical assumptions cannot be justified.
3. Multiple plausible methodologies have materially different implications.
4. The Engineer cannot devise a credible evaluation method.
5. Important evidence is contradictory.
6. Unexpected results undermine the original research hypothesis.
7. Repeated implementation failures suggest a conceptual design problem.
8. A conclusion requires substantial interpretation beyond the observations.
9. A research scope change could invalidate earlier decisions.
10. The system reaches a required stage-review gate.

A critical principle:

**Do not use self-reported confidence to bypass a mandatory review or an objective high-risk trigger.**

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

Used when the Engineer is uncertain how to proceed.

The Advisor should diagnose the problem, identify the conceptual obstacles, propose alternative approaches, compare their merits, and recommend a defensible next action.

**Mode B — Design review**

Used when the Engineer has proposed a research or technical design.

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

Every mandatory review must return a structured decision.

```json
{
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

**Approve** means the artifact passes the defined review criteria, not that its claims are proven.

**Revise** means corrections are required before proceeding.

**Block** means there is a fundamental methodological, safety, or validity problem.

**Inconclusive** means the Advisor lacks sufficient evidence to make a defensible determination.

The workflow controller, not the Engineer, enforces the review verdict.

### 4.5 Preventing superficial peer review

A serious problem arises when the Advisor sees only the Engineer's interpretation of its own work.

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
3. Present the Engineer's interpretation and self-review.
4. Ask the Advisor to identify disagreements, missing evidence, and potential errors.

This reduces the risk of anchoring on the Engineer's conclusions.

It does not eliminate correlated model failures, so independent tests and human escalation remain necessary.

---

## 5. Research workflow design

### 5.1 Research lifecycle

Use four major stages:

```text
RESEARCH REQUEST
       |
       v
  1. PLANNING
       |
  Advisor Review Gate
       |
       v
  2. IMPLEMENTATION
       |
  Advisor Review Gate
       |
       v
  3. EVALUATION & ANALYSIS
       |
  Advisor Review Gate
       |
       v
  4. REPORTING
       |
  Advisor Review Gate
       |
       v
  RESEARCH COMPLETE
```

Each stage contains an autonomous Engineer work loop.

```text
Select task
    |
Assess readiness
    |
    +-- READY ------> Execute
    |
    +-- INVESTIGATE -> Gather evidence -> Reassess
    |
    +-- CONSULT ----> Advisor -> Update approach
    |
    +-- BLOCKED ----> Escalate / Stop
                           |
                      Resume if resolved

After execution:
    |
Verify result
    |
Update evidence and task state
    |
Next task or stage review
```

### 5.2 Stage 1 — Research planning

**Objective:** Transform the user's research direction into an executable, falsifiable research program.

The Engineer should:

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

The Engineer should:

1. Inspect existing code, libraries, and datasets.
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

**Gate:** Relevant tests must pass and the Advisor must accept the implementation as sufficiently ready for the planned evaluation.

Implementation approval does not establish that the scientific hypothesis is correct.

### 5.4 Stage 3 — Evaluation and analysis

**Objective:** Generate reproducible empirical evidence and assess whether the research hypotheses are supported.

The Engineer should:

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
11. Compare observations with competing hypotheses.
12. Document deviations and exploratory findings.

**Required artifacts**

- Immutable experiment configuration snapshots.
- Raw evaluation results.
- Experiment and inference metadata.
- Statistical analysis scripts.
- Metrics and figures.
- Ablation results.
- Failure taxonomy.
- Evidence-to-hypothesis assessment.
- Threats-to-validity analysis.

**Advisor review questions**

- Were the evaluation protocols followed?
- Are the measurements valid?
- Are the comparisons fair?
- Are the statistical methods appropriate?
- Are observed differences practically meaningful?
- Could the effects be explained by confounding variables?
- Have negative results been preserved?
- Do the findings actually support the stated conclusions?

**Gate:** The Advisor must accept the validity of the evidence and its interpretation, or identify the corrective work needed.

Do not modify a held-out evaluation set simply to obtain stronger results. Material protocol changes require a new experiment version and corresponding disclosure.

### 5.5 Stage 4 — Reporting

**Objective:** Produce a rigorous technical report whose claims can be traced to evidence.

The Engineer should prepare a report containing:

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

The Engineer must be an effective consumer of Advisor intelligence.

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

### 6.3 Information prioritization

Include information in this order:

1. The question or decision required.
2. Why it matters to the research objective.
3. The most relevant verified facts.
4. The Engineer's current approach.
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

This avoids paying to transmit large amounts of potentially irrelevant context while retaining the ability to investigate difficult problems deeply.

**Important:** An arbitrary compression target must never override evidence sufficiency.

### 6.5 Consultation quality checks

Before calling the Advisor, the Engineer should verify:

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

If budget is exhausted, suspend or narrow the research rather than silently removing required review.

---

## 7. Research artifacts, knowledge, and memory

### 7.1 Artifacts as the source of truth

Agent chat histories should not be the primary record of research.

Instead, use versioned artifacts.

Each research project should have a stable identifier, persistent tasks, source records, experiment runs, decisions, reviews, and final deliverables.

### 7.2 Suggested project structure

```text
research-project/
├── charter/
│   ├── research-charter.md
│   └── scope-and-constraints.md
│
├── literature/
│   ├── sources.jsonl
│   ├── literature-review.md
│   └── evidence-notes/
│
├── planning/
│   ├── hypotheses.md
│   ├── methodology.md
│   ├── evaluation-plan.md
│   └── roadmap.md
│
├── implementation/
│   ├── src/
│   ├── tests/
│   ├── configs/
│   └── README.md
│
├── experiments/
│   ├── manifests/
│   ├── raw-results/
│   └── analysis/
│
├── reviews/
│   ├── planning/
│   ├── implementation/
│   ├── evaluation/
│   └── reporting/
│
├── decisions/
│   └── decision-log.md
│
├── reports/
│   └── research-report.md
│
└── manifests/
    └── artifact-manifest.json
```

Large datasets, binaries, and experiment outputs may be stored outside Git in content-addressed artifact storage. The manifest should reference their immutable locations and hashes.

### 7.3 Research knowledge organization

I recommend four knowledge categories.

| Knowledge category | Contents |
|---|---|
| Research literature | Papers, theories, concepts, related work |
| Project knowledge | Goals, hypotheses, decisions, constraints |
| Experimental evidence | Methods, configurations, outputs, metrics |
| Operational knowledge | Tools, procedures, previous failures, research practices |

The Engineer should retrieve only the knowledge needed for the active task.

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

The Engineer must not convert a plausible hypothesis into a verified fact merely because the Advisor agrees with it.

---

## 8. Workflow state and execution contracts

### 8.1 Project state

A research project should track:

- Project ID.
- Research direction and goal.
- Active stage and version.
- Tasks and dependencies.
- Research questions and hypotheses.
- Approved methodology.
- Resource budgets.
- Session and run identifiers.
- Artifact references.
- Advisor consultation history.
- Review verdicts.
- Human escalation status.
- Research completion status.

### 8.2 Task state

```typescript
type ResearchTask = {
  id: string;
  projectId: string;
  stage: ResearchStage;
  parentTaskId?: string;
  dependencies: string[];

  objective: string;
  acceptanceCriteria: string[];

  status:
    | "pending"
    | "assessing"
    | "investigating"
    | "consulting"
    | "executing"
    | "verifying"
    | "completed"
    | "blocked";

  readinessAssessment?: ReadinessAssessment;

  engineerSessionId?: string;
  consultationIds: string[];
  artifactIds: string[];
  evidenceIds: string[];

  attemptCount: number;
};
```

A task may be marked complete only after its acceptance criteria have been checked.

### 8.3 State transitions

Use explicit workflow transitions.

```text
CREATED
   |
SCOPING
   |
PLANNING
   |
PLAN_REVIEW
   |---- revise ---> PLANNING
   |
IMPLEMENTING
   |
IMPLEMENTATION_REVIEW
   |---- revise ---> IMPLEMENTING
   |
EVALUATING
   |
EVALUATION_REVIEW
   |---- revise ---> EVALUATING
   |
REPORTING
   |
REPORT_REVIEW
   |---- revise ---> REPORTING
   |
COMPLETED
```

From every active state, the workflow may enter:

- `WAITING_FOR_ADVISOR`
- `WAITING_FOR_HUMAN`
- `BLOCKED`
- `FAILED`
- `SUSPENDED`

Transitions must be persisted.

### 8.4 Controller pseudocode

```typescript
async function runResearch(project: ResearchProject) {
  for (const stage of RESEARCH_STAGES) {
    await enterStage(project, stage);

    while (!stageDeliverablesComplete(project, stage)) {
      const task = await selectNextTask(project, stage);

      const readiness = await engineer.assessReadiness(task);

      if (readiness.status === "INVESTIGATE") {
        await engineer.investigate(task);
        continue;
      }

      if (readiness.status === "CONSULT") {
        const request = await buildConsultationPackage(task);
        const advice = await advisor.consult(request);

        await persistAdvice(advice);
        await engineer.integrateAdvice(task, advice);
        continue;
      }

      if (readiness.status === "BLOCKED") {
        await suspendOrEscalate(project, task);
        return;
      }

      const execution = await engineer.execute(task);

      const verification = await verifyTask(task, execution);

      await persistExecution(execution, verification);
      await updateTaskState(task, verification);
    }

    const reviewPackage = await buildStageReviewPackage(
      project,
      stage
    );

    const review = await advisor.review(reviewPackage);

    await persistReview(review);

    if (review.verdict === "approve" &&
        await mandatoryChecksPass(project, stage)) {
      await advanceStage(project);
      continue;
    }

    await createRemediationTasks(review);

    if (await retryOrBudgetLimitReached(project, stage)) {
      await suspendOrEscalate(project);
      return;
    }

    await resumeStageForRevision(project, stage);
  }

  await finalizeProject(project);
}
```

This is architectural pseudocode, not a complete framework-specific implementation.

Important details for a real implementation include idempotent execution, durable checkpoints, retry handling, atomic state transitions, and prevention of duplicate external actions after recovery.

### 8.5 Bounded autonomy

Use configurable limits for:

- Research iterations.
- Advisor consultations.
- Stage review cycles.
- Experiment runs.
- Runtime.
- Token usage.
- External API expenditure.
- Sandbox resource consumption.

When limits are reached, the Engineer should produce an honest status report identifying completed work, unresolved issues, and the next required decision.

No mechanism should force the Engineer to produce a positive research conclusion when the evidence is insufficient.

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

The Engineer and Advisor must distinguish:

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

---

## 10. Recommended implementation technology

### 10.1 Architectural preference

Use a composable architecture with three distinct layers.

| Layer | Responsibility |
|---|---|
| Workflow engine | Durable research lifecycle and review enforcement |
| Agent harness | Model interaction, tool execution, context management |
| Research infrastructure | Code, evidence, datasets, experiments, artifacts |

Avoid coupling research semantics to framework-specific chat messages.

Project state, consultation records, review decisions, and experiment evidence should remain accessible even if the agent framework changes.

### 10.2 Initial framework recommendation

**Recommended starting point: Mastra with TypeScript.**

Reasons:

- Native agent abstraction.
- Typed workflows and structured steps.
- Conditional branching and loops.
- Workflow persistence and suspension.
- Agent tool integration.
- Observability and usage tracking.
- A coherent implementation environment for both agent behavior and deterministic orchestration.

Mastra's documented capabilities align with the requirement to combine autonomous agent activity with enforced lifecycle stages.

An alternative is **Deep Agents with LangGraph**, particularly when its filesystem-based agent harness and Python ecosystem are more attractive.

The crucial design distinction:

- Mastra is a suitable candidate for both the initial workflow and agent runtime.
- Deep Agents is especially relevant as an opinionated agent harness, supported by LangGraph execution facilities.
- A custom workflow with LangGraph can provide fine-grained control when necessary.

Do not combine several overlapping agent orchestration frameworks in version 1 without a demonstrated requirement.

### 10.3 Suggested initial stack

| Component | Recommendation |
|---|---|
| Language | TypeScript |
| Agent runtime | Mastra Agents |
| Workflow | Mastra Workflows |
| Engineer model | Capable, cost-effective coding/research model |
| Advisor model | Strongest practically available reasoning model |
| Tool execution | Isolated container or sandbox |
| Source control | Git |
| Task and project state | SQLite initially; PostgreSQL when needed |
| Artifacts | Local filesystem initially; object storage later |
| Schemas | Zod |
| Experiment analysis | Python, pandas, SciPy and relevant scientific libraries |
| Literature sources | Academic search and publisher APIs, official documentation, repositories |
| Observability | Structured run events, traces, token/cost records |
| Dashboard | Minimal project/task/review interface |

The two models should be configurable independently by project or task.

The Engineer model must be capable enough to implement and evaluate real experiments. A cheaper model that frequently generates flawed work may increase total cost through rework and Advisor consultations.

### 10.4 Tool permissions

**Engineer tools**

- Literature search and retrieval.
- Repository inspection.
- Filesystem read/write.
- Code editing.
- Terminal execution in a sandbox.
- Test and benchmark execution.
- Dataset processing.
- Statistics and visualization.
- Artifact creation.
- Advisor consultation.
- Project/task updates.

**Advisor tools**

- Read-only artifact inspection.
- Primary-source retrieval.
- Read-only source code inspection.
- Experiment and evaluation result inspection.
- Optional isolated analytical computation.
- Structured review submission.

The Advisor should not modify the Engineer's implementation or alter raw experimental observations.

### 10.5 Security and operational safeguards

Implement:

- Isolated code execution.
- Explicit filesystem boundaries.
- Secret management outside agent-accessible source files.
- Network restrictions where practical.
- Resource quotas.
- Restricted external side effects.
- Protection against prompt injection in retrieved content.
- Validation of tool arguments.
- Separation of trusted instructions from untrusted documents.
- Human approval for irreversible, expensive, externally visible, or security-sensitive actions.

An autonomous research agent will encounter untrusted web pages, repositories, datasets, and executable dependencies. Treat them as data, not instructions governing the agent.

---

## 11. System prompts and agent contracts

### 11.1 Engineer system-instruction template

**Role:** Autonomous Applied AI Research Engineer.

**Mission:** Transform research goals into rigorous, reproducible research results.

**Responsibilities**

- Own research planning, implementation, evaluation, analysis, and reporting.
- Maintain project state, artifacts, evidence and decisions.
- Assess task understanding and readiness before substantial execution.
- Consult the Research Advisor when uncertainty cannot be responsibly resolved.
- Submit completed stage deliverables for mandatory Advisor review.
- Integrate accepted feedback and document unresolved disagreements.
- Use appropriate tools to independently verify claims and implementation results.
- Remain within budget and security constraints.

**Reasoning discipline**

- Distinguish facts, inferences, hypotheses and assumptions.
- Do not fabricate research sources, observations, experiment results, or successful executions.
- Prefer primary evidence when making consequential claims.
- Question approaches that lack identifiable evaluation criteria.
- Preserve unsuccessful experiments and contradictory evidence.
- Do not claim a task has passed merely because generated text appears plausible.
- Do not advance a research stage without controller authorization.

**Advisor consultation discipline**

- Formulate one precise decision or closely related question set per consultation.
- Provide the minimum sufficient context.
- Supply direct references to critical evidence.
- Explain uncertainty and alternative explanations.
- Request actionable feedback.
- Avoid repeating information available in existing decisions.

**Completion discipline**

A task is complete only when its acceptance criteria are satisfied and supporting evidence is recorded.

### 11.2 Advisor system-instruction template

**Role:** Principal Research Scientist and Methodological Advisor.

**Mission:** Improve the theoretical rigor, scientific validity, and intellectual quality of the Research Engineer's work.

**Responsibilities**

- Provide expert theoretical knowledge and methodological guidance.
- Resolve difficult conceptual problems.
- Identify invalid assumptions and missing alternatives.
- Critically evaluate research plans, implementations, evaluations and conclusions.
- Review mandatory stage deliverables.
- Recommend focused corrective actions.
- State when the evidence is insufficient.

**Evaluation discipline**

- Do not agree merely to maintain conversational harmony.
- Do not infer correctness from the Engineer's confidence.
- Challenge assumptions that could materially change conclusions.
- Distinguish established findings from plausible explanations.
- Identify confounding factors and threats to validity.
- Prefer testable recommendations.
- State uncertainty when warranted.
- Request original evidence when summaries are insufficient.

**Response discipline**

- Be concise when the problem is straightforward.
- Reason carefully about high-impact or obscure problems.
- Return structured, decision-oriented responses.
- Prioritize critical issues over cosmetic improvements.
- Provide clear justifications and evidence references.
- Do not represent your own review as independent proof of correctness.

**Authority**

The Advisor provides consultation and structured review verdicts. The workflow controller enforces review policy. Experimental evidence remains authoritative over unsupported model judgment.

---

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
| A | Engineer operating independently |
| B | Engineer with mandatory Advisor stage reviews |
| C | Engineer with mandatory reviews and uncertainty-triggered consultations |
| D | Full architecture with curated consultation packages and adaptive context |

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
- Advisor token consumption.
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
| Engineer misunderstands the question | Detect ambiguity and consult |
| Engineer selects an invalid methodology | Advisor rejects or requests revision |
| Advisor approves incorrect code | Automated tests prevent premature success |
| Advisor receives insufficient context | Requests primary evidence |
| Advisor gives contradictory advice | Engineer records conflict and seeks empirical resolution |
| Experiment returns negative result | Preserve and report honestly |
| Experiment results are inconsistent | Investigate variability and validity |
| Workflow crashes | Resume from persisted state |
| Research budget is exhausted | Suspend and report status |
| Retrieved document contains malicious instructions | Treat as untrusted content |
| Evaluation data is contaminated | Flag the validity threat and stop affected claims |

---

## 13. Implementation roadmap

### Milestone 1 — Two-agent interaction

Implement:

- Research Engineer.
- Research Advisor.
- Advisor consultation tool.
- Structured consultation and review schemas.
- Separate model configurations.
- Basic execution tracing.

**Exit criterion:** The Engineer can autonomously determine when to consult the Advisor and incorporate an actionable response.

### Milestone 2 — Durable research workflow

Implement:

- Four research stages.
- Persistent project and task state.
- Mandatory review gates.
- Revision loops.
- Human escalation.
- Budget limits.
- Recovery after restart.

**Exit criterion:** A research project cannot progress through an unapproved mandatory stage gate.

### Milestone 3 — Research execution

Implement:

- Web and literature retrieval.
- Source provenance.
- Workspace and repository tools.
- Sandboxed code execution.
- Automated testing.
- Experiment runner.
- Artifact management.

**Exit criterion:** The Engineer can implement and reproduce an empirical study end to end.

### Milestone 4 — Scientific evaluation

Implement:

- Experiment versioning.
- Raw result persistence.
- Statistical analysis.
- Claim-to-evidence mapping.
- Independent validation.
- Formal Advisor review rubrics.
- Reproducible report generation.

**Exit criterion:** Every important reported empirical result can be traced to its experimental configuration and underlying observations.

### Milestone 5 — Consultation optimization

Implement:

- Context package generation.
- Consultation-priority policy.
- Selective evidence expansion.
- Advisor decision reuse.
- Token and cost attribution.
- Evaluation of consultation effectiveness.

**Exit criterion:** The system demonstrates measurable improvements in research quality, resource efficiency, or both compared with simpler configurations.

Do not build sophisticated multi-agent memory, automated prompt optimization, or an additional agent orchestration layer before these milestones establish their necessity.

---

## 14. Worked example: Research on prompting and peak LLM performance

**Human research direction**

Investigate the relationship between prompting, domain-specific tasks, and the attainable performance of frontier reasoning models.

**Research objective**

Determine whether prompt optimization primarily improves semantic task specification, capability elicitation, in-context adaptation, or reasoning strategy selection.

### Stage 1 — Planning

The Engineer:

1. Reviews empirical literature on prompting, reasoning, and jagged intelligence.
2. Proposes competing causal hypotheses.
3. Defines controlled task families.
4. Selects frontier models.
5. Designs prompt interventions.
6. Establishes baseline and evaluation metrics.
7. Produces the experiment protocol.

The Advisor evaluates whether the interventions genuinely distinguish the proposed mechanisms.

For example, it may identify that supplying additional domain knowledge is not a valid test of pure capability elicitation, because it changes the information available to the model.

The Engineer revises the plan accordingly.

### Stage 2 — Implementation

The Engineer creates:

- Prompt-variant generator.
- Semantic equivalence validation process.
- Model execution adapter.
- Experiment configuration.
- Evaluators.
- Repetition and sampling controls.
- Result storage and analysis scripts.

The Advisor reviews the design and inspects evidence that the implementation matches the experiment protocol.

### Stage 3 — Evaluation

The Engineer executes the benchmark and measures:

- Baseline accuracy.
- Optimized accuracy.
- Recovery rate.
- Regression rate.
- Prompt sensitivity.
- Cross-domain transfer.
- Inference cost.
- Statistical uncertainty.

Suppose the results suggest that semantically equivalent prompt variations have little effect on easy extraction tasks but substantial effects on unfamiliar reasoning tasks.

The Engineer should not immediately conclude that different internal reasoning circuits were activated.

The Advisor challenges that interpretation and asks whether variation in answer formatting, stochastic sampling, or computational budget can explain the observations.

Additional experiments are conducted if justified by the expected information gain and remaining budget.

### Stage 4 — Reporting

The Engineer prepares a report that distinguishes:

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
| Number of agents | Exactly two |
| Primary owner | Research Engineer |
| Strongest reasoning model | Research Advisor |
| Orchestration | Deterministic workflow controller |
| Agent autonomy | Within bounded research stages |
| Advisor access | Consultation plus mandatory reviews |
| Review enforcement | Application-level state machine |
| Confidence assessment | Structured readiness checks, not arbitrary scores |
| Consultation context | Compact packages with expandable evidence |
| Shared memory | Versioned artifacts and research state |
| Research validation | Executable evidence and independent evaluation |
| Human involvement | Material decisions and unresolved exceptions |
| Technology | Start with a single coherent stack |
| Expansion strategy | Add features only when evaluations justify them |

### Final architectural principle

**The system should maximize the amount of scientifically reliable research accomplished per unit of human attention and computational resources.**

The Research Engineer provides execution capacity, persistence, and disciplined research operations.

The Research Advisor provides high-value reasoning, theoretical depth, methodological scrutiny, and intellectual challenge.

The workflow controller provides enforceable structure.

The experiment and evidence infrastructure provides the foundation for determining whether their work is actually correct.

The central measure of success is not how independently the agents converse, how often they agree, or how impressive their final reports appear.

It is whether the system can repeatedly produce useful, verifiable, reproducible research with limited human intervention and a defensible cost.

---

## Technical and research references

- [Pi coding agent](https://docs.pi.dev/latest)
- [Pi Subagents - Agent](https://github.com/nicobailon/pi-subagents/blob/main/docs/agents.md)
- [Pi Subagents - AgeWorkflows and orchestrationnt](https://github.com/nicobailon/pi-subagents/blob/main/docs/workflows.md)