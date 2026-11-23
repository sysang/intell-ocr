# Research Lead assignment ledger: Create–Retrieve–Update analysis

**Status:** Historical design review of blueprint v1.2. The standalone task ledger proposed here is superseded by [blueprint v1.4 §8.9](blueprint-v1.md#89-assignment-ledger-and-delegation-lifecycle): Beads manages operational tasks; the project ledger preserves exact execution and acceptance evidence. This note records the original rationale, not a current implementation plan.

## Finding in v1.2

Blueprint v1.2 described a Lead-owned assignment lifecycle but did not specify a full Create–Retrieve–Update (CRU) ledger over typed resources. It lacked exact lookup by resource ID, combined full-text search and structured filters, and relational resource categories for document sections. The v1.4 design addresses task lookup and combined queries through Beads, and keeps historical execution records in the project ledger. It does not require a second task index or the custom category model below. See the [tool README](tools/research-ops/README.md) for verification status.

The ledger must answer three separate questions: **What was authorized? What actually ran and came back? What may the research rely on?** An assignment revision answers the first, run attempts and results answer the second, and the Lead's acceptance decision answers the third. A completed Pi run is not accepted work; accepted work is not an Advisor gate approval.

## Gaps in v1.2

Section numbers in this table refer to v1.2, before the lifecycle was consolidated into §8.9.

| Requirement | v1.2 design | Gap identified at the time |
|---|---|---|
| **CREATE** | §8.3 defined a work package, structured result, and Lead acceptance. §10.4 required persisting intent before `subagent` dispatch and attaching the Pi run ID after launch. | Revisions, attempts, results, and decisions do not each have defined identities and relationships. The Pi run ID cannot identify an attempt before launch. |
| **RETRIEVE by ID** | Assignment, run, and artifact references carry IDs. | There is no exact lookup contract for an individual assignment, historical revision, attempt, result, or decision. The prototype's `show` reads a top-level section. |
| **RETRIEVE by query** | §8.8 defined fixed views such as `status`, `next`, and `progress`. | No ledger query combines full-text search with filters. OKF hub retrieval is separate and does not fill this gap. |
| **UPDATE** | The Lead is instructed to record readiness, attach a run ID, reconcile, accept or reject, and checkpoint workspace-changing deliveries. | No formal assignment transition interface defines guards, replay behavior, or what happens when a result arrives from an earlier attempt. |
| **No DELETE** | There is no proposed delete operation; dropped optional work leaves a recorded gap. | The design does not explicitly require old revisions, failed attempts, and superseded decisions to remain individually retrievable. |
| **Document section = resource category** | The design groups information into JSON sections and document files. | There are no relational category records or explicit links from resources to the categories that determine section membership. |

At the time of the review, the prototype stored basic assignment fields and one run ID. It had no assignment-specific transitions or attempt history. All 16 original ledger tests passed, even though the validator accepted an assignment with an invalid status and missing required fields and the status view ignored it.

## Original resource proposal

| Resource category / document section | One record represents | Relationship |
|---|---|---|
| Assignments | A stable work item, e.g. `WORK-014` | Belongs to a project |
| Assignment revisions | An exact brief: scope, pinned inputs, grants, checks, and budget | Belongs to one assignment |
| Run attempts | One dispatch intent and its observed execution state | Belongs to one revision; Pi run ID can initially be unknown |
| Results | A returned deliverable, evidence references, and gaps | Belongs to one attempt |
| Acceptance decisions | What the Lead accepted or rejected, why, and against which evidence | References the exact result and revision |
| Dependencies | What must be available before launch or what relies on an accepted output | Links a revision to another assignment or gate, with direction and requiredness |

Each resource has a stable ID and a `category_id` foreign key. A category has a stable key, display label, and display order. A section is rendered from its category; renaming the section does not change record IDs. **Blocked assignments** is a filtered view, not a new category that duplicates records. Keep one authoritative ledger; document and status views are derived from it, not separately editable copies.

## Operation semantics

- **CREATE:** Create the assignment and its first revision. Before dispatch, persist a new attempt ID even if no Pi run ID is known. Record results and decisions as distinct resources. A retry against the same brief creates another attempt; changing scope, pinned inputs, or grants creates another revision.
- **RETRIEVE by ID:** Read exactly the requested resource, including historical revisions and attempts. Optionally include linked resources; never substitute the current revision for an explicitly requested historical one.
- **RETRIEVE by query:** Support full-text search alone, structured filters alone, and both together. Search authorized titles, briefs, summaries, blockers, and rationale. Filter by category, cycle, assignee, readiness, acceptance, dates, and related run state. Keep run state separate from acceptance state. Use stable sorting and pagination; return resource IDs, categories, matching snippets where applicable, and links. Reference large or sensitive artifacts rather than indexing them by default.
- **UPDATE:** Use named, guarded updates such as `mark-ready`, `attach-run`, `mark-launch-unknown`, and `record-integration`. Record who changed what, when, and why. Issued briefs and recorded decisions are not rewritten in place; supersede them with new records. Replaying a completion or decision write must not duplicate it. Cancelled, dropped, and superseded records remain retrievable even if omitted from active views. Do not expose DELETE.

Superseded interface sketch (do not implement these task commands in `ledger.py`):

```text
ledger get WORK-014 --include revisions,attempts,results,decisions
ledger query --category assignments --text '"OCR fixture"' \
  --filter assignee=engineering-worker --filter acceptance=pending \
  --filter latest_attempt.run_state=launch_unknown
```

## Original recovery example and enhancement order

The Lead assigns an OCR test fixture to `engineering-worker`, records revision `R1` and attempt `A1`, then calls `subagent`. If the host stops after Pi launches but before the run ID is recorded, the next Lead session retrieves `A1` and `R1`, records an unknown launch outcome until reconciled, and checks the workspace against the recorded base. A missing run ID is not proof that nothing started. Do not start another writer in the same workspace until the first attempt and its effects are reconciled. A safe retry creates `A2`; a late `A1` result remains linked to `A1` and cannot close `A2`. Once the Lead verifies and accepts the fixture, dependents wait for the workspace integration checkpoint. The Advisor readiness review is still required before full evaluation.

1. **Define the schema and interface together:** resource IDs and categories, relationships, exact lookup, combined search and filtering, and guarded write transitions.
2. **Prove one single-writer path:** test interruption before launch, after launch but before run-ID recording, after files change, and after verification but before checkpointing. Verify what the pinned Pi runtime can actually correlate on resume; do not promise exactly-once launch.
3. **Prove a read-only pool path:** show that the ledger works without a Git diff and that optional failure does not block independent or gate work that does not depend on it. Test exact historical lookup, combined queries, and rejection of late or mismatched results.
4. **Extend role coverage and status views:** reuse tracking mechanics for Advisor, architect, and OKF calls while preserving their own result contracts. Expand to concurrent worktrees only after single-writer recovery is reliable.

Preserve [fixed-roster-first routing](blueprint-v1.md#35-delegate-concrete-self-contained-work), [dependency-scoped HOLD and escalation](blueprint-v1.md#86-director-communication-contract), and the Lead's ownership of acceptance. Keep `subagent` as the dispatch mechanism; the ledger neither schedules work nor grants tool permissions. Permission enforcement remains at the host/tool boundary.
