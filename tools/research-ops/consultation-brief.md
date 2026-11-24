# Lead consultation brief (v1)

Use this checklist and template for a versioned, decision-oriented Advisor brief or a specialist's domain-advice request. The [Blueprint §§4.4–4.5, 6](../../blueprint-v1.md#44-advisor-decision-contract) governs review, evidence expansion, and advice. A brief is not approval, a launch reservation, or a token limit. Use only the approved project/runtime envelope.

## Before sending

- Name one specific question, the decision the Lead owns, and why the answer matters now. Link the exact task assessment, if applicable.
- Separate established facts from assumptions and competing hypotheses. Include material alternatives and failure modes, or give a reason none apply.
- Link accessible, versioned primary evidence and the sections that matter. Would the missing information change the recommendation? If so, include it, seek it explicitly, or block; do not compress it away.
- Ask for actionable output: what to do, why, what is unresolved, and what evidence would change the advice. For a gate, include the rubric and exact phase and `manifest-id@version`; require the §4.4 verdict contract.
- For non-mandatory advice, check for an earlier disposition on the same question and unchanged evidence, assumptions, and constraints. Do not treat a similar question as equivalent. **Mandatory consultations and gate verdicts require their own calls and results.** Reserve the call with the approved per-call limits, issue retry limit, and budget category as specified in the [accounting runbook](README.md#advisor-consultation-accounting). This checklist does not enforce provider limits.

## Decision brief template

```markdown
# <consultation-id>@<version> — <Advisor mode or specialist domain>

- Decision and impact: <one specific question; why it matters>
- Research context: <objective, stage, exact task ID and assessment ID>
- Established facts: <claim — primary evidence ref, version, and section>
- Current approach: <method and rationale>
- Uncertainty: <assumptions, alternative hypotheses, known failure modes>
- Evidence to inspect: <small set of versioned project artifact refs, exact sections>
- Constraints: <budget category and remaining allowance; per-call/issue limits;
  authorized access and implementation constraints>
- Requested output: <actionable recommendation and remaining uncertainty,
  or gate, phase, manifest version, rubric, and §4.4 contract>
```

Give the initial brief and selected evidence in fresh context. Do not include credentials, full conversations, or unrelated data. Expand only in response to specific evidence needs. At a gate, retain the original rubric and prior findings, version changed submissions, and respect §4.4's evidence expansion and no-verdict bounds. Keep actual run and result evidence, not reconstructed run references.

## High-risk review: avoid priming the first pass

1. Provide only the research question, relevant primary evidence and the rubric, without the Lead's conclusions or self-review. Request an independent assessment and preserve it (run reference, evidence inspected, findings, and gaps). The first pass does **not** issue a gate verdict.
2. Send that assessment with the Lead's interpretation and self-review. Ask the Advisor to compare them and identify disagreements, missing evidence, and possible errors. Pin both briefs and output artifacts. If the evidence changes materially, reconcile the coverage and repeat the evidence-first pass where needed. For a gate, record only the second pass's manifest-bound §4.4 verdict as the verdict. Both calls consume mandatory slots. Independent tests and human escalation still apply.

## After receiving advice

Record the exact child run, outcome, and durable evidence. For a task-linked completed consultation, the Lead records `accepted`, `adapted`, or `declined` with rationale and the pinned result. If empirical checks later validate or contradict the advice, version and link those observations separately; completion or adoption alone is not validation. Missing, contradictory, or unusable advice does not unblock dependent work. See the [ledger commands](README.md#task-readiness-and-routing) for what is checked locally.
