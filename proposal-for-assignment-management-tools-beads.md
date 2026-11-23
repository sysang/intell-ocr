# Guideline: Build Beads-Powered Pi Tools for Research Lead

**Target:** Pi Research Lead agent  
**Task-management backend:** Beads v0.49.6 (SQLite)  
**Implementation language:** TypeScript  
**Deliverable:** Project-local Pi extension exposing Beads CLI functionality as custom tools

## 1. Context and Purpose

The **Research Lead** is the main Pi agent responsible for autonomously conducting research projects. Its responsibilities include planning, investigation, task decomposition, delegation to subagents, implementation coordination, evaluation, analysis, and reporting.

To operate effectively over long-running research projects, the Research Lead needs a persistent, queryable task-management mechanism.

Without such a mechanism, the agent must repeatedly reconstruct its outstanding work, dependencies, assignments, and progress from conversation history or scattered project files. This increases context consumption and makes task coordination and session recovery unnecessarily difficult.

The objective is to provide the Research Lead with local task-management capabilities through **custom Pi tools backed by Beads**.

These tools should allow the agent to:

- Organize research work into manageable tasks.
- Search and retrieve relevant work efficiently.
- Track task status, priority, dependencies, and ownership.
- Discover which tasks can be executed next.
- Maintain traceability between discovered problems and originating work.
- Coordinate assignments to subagents and monitor unfinished work.
- Resume task management after interruptions or new Pi sessions.

The implementation must remain lightweight. Beads already implements the underlying task-management logic, so the task is primarily to expose its useful CLI functionality through Pi's tool interface.

**Scope boundary:** These tools manage tasks and operational assignments. They do not replace `pi-subagents`, research-stage governance, Advisor review gates, or the existing project-state ledger.

## 2. Expected Capabilities (Requirements)

### 2.1 Mandatory: Task CRUD without Delete

The toolset must support the following operations:

| Operation | Required capability |
|---|---|
| CREATE | Create a task with title, description, type, priority, and available metadata |
| RETRIEVE by ID | Fetch a specific task using its unique identifier |
| RETRIEVE by query | Search tasks by text and filter by structured metadata |
| UPDATE | Modify an existing task's fields, assignment, or status |
| DELETE | Explicitly excluded |

Retrieval is particularly important.

The Research Lead must be able to ask questions such as:

- Find all unfinished tasks related to evaluation.
- Find tasks assigned to `engineering-worker`.
- Find high-priority tasks associated with the current research cycle.
- Find the exact task identified by a known ID.
- Find tasks completed previously to avoid repeated work.

**Text search and structured filtering must be combinable**, rather than requiring the agent to fetch every task and inspect results manually.

For the initial implementation, Beads' native lexical search is sufficient if tests demonstrate that it meets these use cases. Do not assume semantic search, relevance ranking, stemming, or SQLite FTS5 unless verified.

### 2.2 Required: Assignment Management

The Research Lead must be able to:

1. Create work items suitable for delegation.
2. Assign an item to a designated subagent.
3. Identify assigned, unassigned, unfinished, and completed work.
4. Track execution progress and record blockers.
5. Find work requiring reassignment or recovery.
6. Close tasks when the Lead has accepted the deliverable.

A Beads task and a Pi execution run are different things.

For example, task `bd-abc` may correspond to assignment `WORK-014`, which may be attempted through more than one Pi subagent run.

Beads should contain the operational task record. The existing research project ledger continues to preserve authoritative assignment attempts, Pi run IDs, verification evidence, and acceptance decisions.

The Pi tools should facilitate this workflow without creating another delegation engine.

### 2.3 Required: Agent-Friendly Operation

Every tool should provide:

- Strongly typed input parameters.
- Structured, machine-readable output.
- Explicit error handling.
- Concise results suitable for an LLM context window.
- No requirement for the Research Lead to construct shell commands.
- Deterministic CLI invocation.
- Durable task storage across Pi sessions.

Do not expose a generic `bd_execute(command: string)` tool. Implement semantic wrappers instead.

### 2.4 Advanced Capabilities That Add Productivity

Besides basic CRUD, prioritize:

| Capability | Research Lead benefit |
|---|---|
| Task dependencies | Understand prerequisite work and execution order |
| Ready-work discovery | Find tasks that are no longer dependency-blocked |
| Blocked-work discovery | Identify scheduling bottlenecks |
| Epics and subtasks | Decompose larger research objectives |
| `discovered-from` relationships | Preserve provenance of unexpectedly discovered work |
| Task labels and priorities | Organize and prioritize the backlog |
| Comments and notes | Record concise task-local progress and blockers |
| Stale-work detection | Find tasks that may need inspection |
| Statistics and summaries | Obtain a quick operational overview |
| Atomic task claiming | Optional future support for concurrent autonomous workers |

These features should be exposed incrementally, starting with dependency-aware work discovery.

---

## 3. Beads v0.49.6 Overview

**Beads** is a local, agent-oriented issue/task tracker accessed through the `bd` command-line interface.

Relevant properties of the selected v0.49.6 release:

- Local installation.
- SQLite-capable storage.
- CLI-based task operations.
- JSON output for programmatic integration.
- Persistent issue identifiers.
- Task metadata and status.
- Dependencies and relationships between tasks.
- Ready-work discovery.
- Agent-oriented issue tracking.

Version v0.49.6 is deliberately pinned. Do not install or use the latest version when implementing this integration, since newer releases have materially different storage and command surfaces.

### 3.1 Reference Documentation

Use these sources:

1. [Beads v0.49.6 README](https://github.com/gastownhall/beads/blob/v0.49.6/README.md)
2. [Beads v0.49.6 CLI Reference](https://github.com/gastownhall/beads/blob/v0.49.6/docs/CLI_REFERENCE.md)
3. [Pi Extensions — Custom Tools](https://docs.pi.dev/latest/extensions#custom-tools)

The first two sources define the intended Beads version. The third defines how custom Pi tools must be registered and executed.

**Important verification instruction:** The pinned GitHub files were not directly accessible during preparation of this guide. Treat the CLI mapping below as the implementation checklist, not proof that every flag has been verified. Inspect the exact v0.49.6 binary and its local help before coding. Do not borrow undocumented commands or flags from newer Beads releases.

### 3.2 Verify the Local Beads Installation

From the research repository root, run:

```bash
bd version
bd --help
bd create --help
bd show --help
bd list --help
bd search --help
bd update --help
bd close --help
bd ready --help
bd blocked --help
bd dep --help
bd dep add --help
```

Also inspect the relevant optional commands:

```bash
bd comments --help
bd label --help
bd stale --help
bd status --help
bd reopen --help
```

The installed version must be **v0.49.6**.

Verify the active project uses the intended local SQLite backend. Do not run a database initialization command against a valuable existing workspace merely to test the integration.

Record any difference between the pinned documentation, the help output, and the commands proposed below. The verified executable takes precedence for actual behavior.

---

## 4. Functional Parity: Requirements vs. Beads CLI

The integration should primarily wrap existing Beads operations, not reimplement them.

### 4.1 Core Functional Parity

| Requirement | Beads CLI | Pi tool to implement |
|---|---|---|
| Create task | `bd create` | `bd_create` |
| Retrieve task by ID | `bd show` | `bd_get` |
| Search by text | `bd search` | `bd_query` |
| Filter by metadata | `bd list`, `bd search` | `bd_query` |
| Update task | `bd update` | `bd_update` |
| Close completed task | `bd close` | `bd_close` |
| Reopen task | `bd reopen` | `bd_reopen` (optional) |

**Assessment:** The documented Beads command family covers the mandatory requirements at the operation level.

The implementation must still verify which text fields are searched, how filters combine, how JSON is shaped, and how closed tasks are included.

### 4.2 Advanced Functional Parity

| Advanced requirement | Beads capability | Proposed tool |
|---|---|---|
| Retrieve executable tasks | `bd ready` | `bd_ready` |
| Retrieve dependency-blocked tasks | `bd blocked` | `bd_blocked` |
| Create dependencies | `bd dep add` | `bd_dependency` |
| Inspect dependency relationships | `bd dep list`, `bd dep tree` | `bd_dependency` |
| Remove incorrect dependency | `bd dep remove` | `bd_dependency` |
| Create epics/subtasks | `bd create` with hierarchy options | `bd_create` |
| Preserve discovered-work provenance | `discovered-from` relationship | `bd_dependency` |
| Assign a task | `bd update --assignee` | `bd_update` |
| Add progress comments | `bd comments` command family | `bd_comment` |
| Apply labels | `bd label` command family | `bd_label` |
| Identify stale tasks | `bd stale` | `bd_stale` |
| Review task statistics | `bd status` | `bd_status` |

The exact flags and JSON availability for the advanced commands are subject to the v0.49.6 verification step.

### 4.3 Capabilities Beads Does Not Replace

Some responsibilities cannot be implemented simply by wrapping Beads:

| Capability | Existing mechanism |
|---|---|
| Launch a subagent | Pi `subagent` tool |
| Retrieve Pi run/session status | Pi Subagents runtime |
| Verify work-package acceptance criteria | Research Lead |
| Store authoritative assignment attempts | Research project ledger |
| Enforce PLAN_GATE/CYCLE_GATE/REPORT_GATE | Existing research governance |
| Approve research-stage transitions | Research Lead plus required Advisor verdict |

Do not implement these inside the Beads extension.

The assignment workflow will use Beads tools alongside the existing mechanisms.

---

## 5. Implement the Pi Custom Tools

### Step 1 — Understand the Pi Extension API

Pi supports project-local TypeScript extensions.

A custom tool is registered using:

```typescript
pi.registerTool({
  name: "...",
  label: "...",
  description: "...",
  parameters: ...,
  async execute(toolCallId, params, signal, onUpdate, ctx) {
    // Implementation
  },
});
```

The important elements are:

- `name`: the tool identifier visible to the model.
- `description`: explains when and why the tool should be used.
- `parameters`: JSON Schema-compatible input definition.
- `execute`: implements the operation.
- `content`: human/model-readable tool result.
- `details`: structured result information.

Use TypeBox for parameter schemas.

For CLI execution, prefer `pi.exec()` because it supports argument arrays, explicit working directories, cancellation, and timeouts without introducing a shell.

### Step 2 — Create the Project-Local Extension

Use this location:

```text
.pi/
└── extensions/
    └── beads-tools/
        ├── index.ts
        ├── cli.ts
        └── tests/
```

`index.ts` registers Pi tools. `cli.ts` contains the shared Beads CLI execution helper.

Keep this implementation independent of the Research Lead's prompt file.

Project-local extensions are discovered by Pi when the project is trusted. During development, an extension can also be loaded explicitly with:

```bash
pi -e .pi/extensions/beads-tools/index.ts
```

### Step 3 — Implement a Shared Beads CLI Executor

Create `cli.ts`:

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export function createBeadsClient(pi: ExtensionAPI) {
  async function execute(
    args: string[],
    cwd: string,
    signal?: AbortSignal
  ): Promise<string> {
    const result = await pi.exec("bd", args, {
      cwd,
      signal,
      timeout: 15000,
      maxBuffer: 2 * 1024 * 1024,
    });

    if (
      result.code !== 0 ||
      result.killed ||
      result.truncated
    ) {
      throw new Error(
        `Beads command failed: ${result.stderr || result.stdout}`
      );
    }

    return result.stdout.trim();
  }

  async function json(
    args: string[],
    cwd: string,
    signal?: AbortSignal
  ): Promise<unknown> {
    const output = await execute(
      [...args, "--json"],
      cwd,
      signal
    );

    try {
      return JSON.parse(output);
    } catch {
      throw new Error(
        "Invalid JSON returned by Beads"
      );
    }
  }

  return { execute, json };
}
```

**Implementation requirements:**

- Never interpolate untrusted values into shell command strings.
- Pass CLI parameters as separate arguments.
- Use the current, approved project workspace.
- Check exit codes, termination, and truncated output.
- Preserve cancellation.
- Parse JSON only for commands whose `--json` support has been verified.
- Never interpret a failed command as an empty successful result.
- Do not access SQLite directly.

For mutations where the CLI returns plain text, execute the command and retrieve the resulting task through `bd show --json` when appropriate.

### Step 4 — Implement `bd_create`

**Purpose:** Create tasks, epics, and subtasks.

Expected arguments:

- `title`: required.
- `description`: optional for general tasks; expected for delegated work.
- `type`: defaults to `task`.
- `priority`: defaults to 2.
- `assignee`: optional.
- `parent`: optional.
- `labels`: optional.

Representative Beads command:

```bash
bd create "Implement retrieval benchmark" \
  --description "Implement baseline and evaluation runner" \
  --type task \
  --priority 2 \
  --json
```

Example Pi registration in `index.ts`:

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { createBeadsClient } from "./cli.js";

export default function (pi: ExtensionAPI) {
  const bd = createBeadsClient(pi);

  pi.registerTool({
    name: "bd_create",
    label: "Create Beads Task",
    description:
      "Create a persistent task or epic for research work.",
    parameters: Type.Object({
      title: Type.String({ minLength: 1 }),
      description: Type.Optional(Type.String()),
      type: Type.Optional(
        Type.Union([
          Type.Literal("task"),
          Type.Literal("epic"),
          Type.Literal("bug"),
          Type.Literal("feature"),
        ])
      ),
      priority: Type.Optional(
        Type.Integer({ minimum: 0, maximum: 4 })
      ),
      parent: Type.Optional(Type.String()),
    }),

    async execute(_id, params, signal, _update, ctx) {
      const args = [
        "create",
        params.title,
        "--type", params.type ?? "task",
        "--priority", String(params.priority ?? 2),
      ];

      if (params.description !== undefined) {
        args.push("--description", params.description);
      }

      if (params.parent !== undefined) {
        args.push("--parent", params.parent);
      }

      const data = await bd.json(args, ctx.cwd, signal);

      return {
        content: [{
          type: "text",
          text: JSON.stringify(data),
        }],
        details: { data },
      };
    },
  });
}
```

This is the reference implementation pattern for the remaining tools.

Add `assignee` and `labels` once their exact flags have been verified.

**Acceptance test:** Create a task and confirm its returned ID can be retrieved by `bd show`.

### Step 5 — Implement `bd_get`

**Purpose:** Retrieve one task by ID.

CLI:

```bash
bd show <task-id> --json
```

Schema:

```typescript
Type.Object({
  task_id: Type.String({ minLength: 1 }),
})
```

The implementation should call:

```typescript
bd.json(
  ["show", params.task_id],
  ctx.cwd,
  signal
)
```

Return the task's native fields in a normalized object, preserving unknown or optional metadata when possible.

Do not discard dependency information that may be relevant to the Research Lead.

**Acceptance test:** Retrieve a known task and verify its ID, status, description, priority, and assignee.

### Step 6 — Implement `bd_query`

**Purpose:** Support text search and structured filtering.

Use one unified Pi tool instead of making the Research Lead choose between `bd list` and `bd search`.

Recommended inputs:

```typescript
{
  text?: string;
  status?: string;
  type?: string;
  assignee?: string;
  priority?: number;
  label?: string;
  limit?: number;
}
```

Dispatch logic:

- If a text query is supplied, use `bd search`.
- Otherwise, use `bd list`.
- Append only CLI-supported filter flags.
- Default to a bounded result count, such as 20.
- Preserve support for including closed tasks.
- Return compact issue summaries rather than full descriptions.

Example:

```bash
bd search "evaluation" --status open --json

bd list --assignee engineering-worker --json
```

Verify that combining text and metadata filters applies the intended AND semantics. Test case sensitivity, searched fields, and empty-query behavior.

**Crucial:** Do not implement hidden post-filtering that silently loses matches because Beads returned only a limited candidate set.

Return metadata indicating when results may be incomplete.

### Step 7 — Implement `bd_update`

**Purpose:** Update existing task fields and operational status.

Recommended inputs:

```typescript
{
  task_id: string;
  title?: string;
  description?: string;
  priority?: number;
  assignee?: string;
  status?: string;
  notes?: string;
}
```

Build the CLI argument array using only fields explicitly supplied.

Examples:

```bash
bd update <task-id> \
  --assignee engineering-worker \
  --json

bd update <task-id> \
  --status in_progress \
  --json

bd update <task-id> \
  --priority 1 \
  --json
```

Verify valid status values against the pinned CLI.

Avoid using this tool to perform task closure. Provide `bd_close` for the completion operation.

After updating, retrieve the task if needed to confirm its actual state.

### Step 8 — Implement `bd_close` and Optional `bd_reopen`

**Purpose:** Complete accepted work and reopen tasks when necessary.

CLI:

```bash
bd close <task-id>
bd reopen <task-id>
```

Check whether the selected release supports JSON for these commands. If not, inspect their exit status and retrieve the task afterward.

The Research Lead must verify work before closure.

A successful Pi subagent run alone does not satisfy this condition. The existing assignment-acceptance record remains authoritative.

`bd_reopen` is useful for correcting premature closure or responding to invalidated work, but it can be deferred until needed.

### Step 9 — Implement `bd_ready` and `bd_blocked`

These are among the most valuable tools for routine autonomous research.

CLI:

```bash
bd ready --json
bd blocked --json
```

The tools should support optional priority, assignee, and result-limit filters when available.

**`bd_ready`** returns candidate tasks whose task-level blocking dependencies have been satisfied.

**`bd_blocked`** returns tasks blocked by dependencies, including their blocker relationships when available.

Prefer concise output:

```json
{
  "tasks": [
    {
      "id": "bd-example",
      "title": "Implement baseline",
      "priority": 1,
      "status": "open"
    }
  ],
  "truncated": false
}
```

Do not interpret `bd ready` as approval to dispatch work. The Research Lead must still check the relevant research-stage approval, readiness assessment, permissions, and budget.

### Step 10 — Implement `bd_dependency`

**Purpose:** Create, remove, and inspect dependencies and provenance relationships.

Use an action parameter:

- `add`
- `remove`
- `list`
- `tree`

CLI operations:

```bash
bd dep add <task-id> <prerequisite-id>

bd dep add <task-id> <origin-id> \
  --type discovered-from

bd dep list <task-id>

bd dep tree <task-id>
```

Verify exact argument direction and accepted dependency types against v0.49.6.

Support at least:

- `blocks`: work ordering.
- `discovered-from`: origin/provenance of newly discovered tasks.

Where supported and appropriate, expose additional relationship types without introducing a new graph model.

Do not treat parent-child hierarchy as a blocking dependency unless explicitly required by Beads' verified semantics.

Tests must establish that:

- A prerequisite prevents dependent work from appearing ready.
- Closing the prerequisite makes the dependent work eligible.
- A `discovered-from` relationship does not itself block execution.
- Invalid or cyclic blocking relationships are rejected.

### Step 11 — Implement `bd_comment` and `bd_label`

These tools provide task-local annotation and organization.

For `bd_comment`, wrap the verified v0.49.6 `bd comments` add/list operations.

Typical comments include:

- Implementation progress.
- An encountered blocker.
- A concise result summary.
- A reference to the Pi assignment or run.
- A reason for reopening work.

For `bd_label`, wrap the verified label add/remove/list operations.

Possible labels include:

```text
research-cycle-1
implementation
evaluation
high-risk
needs-review
```

Do not invent a large mandatory label taxonomy. Begin with labels that the Research Lead actually uses for retrieval and filtering.

Store references and concise task-local information in Beads; keep full research evidence in the project workspace.

---

## 6. Add Advanced Productivity Features

After the core tools work, add the following capabilities in the suggested order.

### 6.1 Epics and Subtasks

Extend `bd_create` to support hierarchy via the pinned release's parent option.

Example:

```text
Epic: Evaluate New Retrieval Approach
├── Prepare benchmark dataset
├── Implement baseline
├── Implement proposed retrieval method
├── Run evaluation
└── Analyze results
```

Use this to represent bounded work packages within a research objective.

The Research Lead should create children when decomposition provides better delegation, dependency management, or progress visibility—not mechanically for every trivial action.

### 6.2 Discovered-Work Tracking

When research uncovers new work, the Lead should create a new task and link its origin through `discovered-from`.

For example:

```text
Original task:
Run retrieval benchmark

Discovered task:
Investigate anomalous evaluation scores
```

This preserves provenance and supports later analysis of unexpected research findings.

The Lead should not automatically execute every discovered task. It must evaluate the task's relevance, priority, scope, and authorization.

### 6.3 Stale Task Detection

Implement `bd_stale` using the pinned CLI's supported stale-work command and flags.

Use it to find tasks with no recent recorded activity.

Treat the results as **inspection candidates**, not evidence that a worker has failed or a task has been abandoned.

Cross-check with Pi run status before retrying or reassigning work.

### 6.4 Operational Summary

Implement `bd_status` over the CLI's status/statistics capability.

The goal is to answer routine questions such as:

- How much work remains open?
- What is currently in progress?
- What work is blocked?
- How much work has been completed?

Use concise, structured output.

Avoid generating a separate dashboard or maintaining duplicate statistics if the CLI already computes them.

### 6.5 Atomic Claiming — Optional

If v0.49.6 supports atomic claiming through `bd update --claim`, consider exposing it only when multiple authorized agents can independently select work from a shared queue.

For the initial Research Lead architecture, **prefer explicit Lead-controlled assignment**.

Automatic claiming is unnecessary while the Lead is the sole dispatcher, and it must never bypass fixed-role assignment rules.

### 6.6 Persistence and Synchronization

If Beads' export or synchronization operations are required by the research environment, verify and expose only the necessary operations.

Do not make synchronization an implicit side effect of every model-facing tool.

The existing Git checkpoints, artifact manifests, and research project state must remain consistent with any exported or synchronized task data.

---

## 7. Validate the Integration Through a Realistic Workflow

Use a disposable research project.

### Scenario: Implement and Evaluate a Research Method

**1. Create a research epic.**

Use `bd_create` to create an epic representing the evaluation objective.

**2. Create child tasks.**

Create tasks for:

- Dataset preparation.
- Baseline implementation.
- Proposed method implementation.
- Evaluation execution.
- Results analysis.

**3. Establish execution dependencies.**

Use `bd_dependency` so the evaluation task depends on the necessary implementations and dataset.

**4. Query available work.**

Call `bd_ready`.

Confirm that dependent evaluation tasks are not returned prematurely.

**5. Prepare a real assignment.**

The Lead assesses task readiness, selects the eligible subagent, and records the work package and assignment attempt in the existing project ledger.

Use `bd_update` to record operational ownership.

**6. Delegate through Pi Subagents.**

The Lead calls `subagent` directly, passing the assigned specification.

Record the returned Pi run/session references through the existing assignment-tracking mechanism.

**7. Track progress.**

Use `bd_update` and `bd_comment` to record operational changes.

**8. Verify completion.**

The Lead inspects the returned evidence and records acceptance or rejection.

On acceptance, call `bd_close`.

**9. Query new ready work.**

Call `bd_ready` again.

Confirm that completing prerequisites unlocks dependent tasks.

**10. Simulate a session interruption.**

Start a new Research Lead session.

Use `bd_query`, `bd_get`, `bd_ready`, and `bd_blocked` to reconstruct the operational backlog.

Reconcile the actual Pi run status and authoritative assignment records before continuing.

This scenario is the primary end-to-end acceptance test.

---

## 8. Engineering Quality Requirements

The wrapper implementation should follow these practical rules.

### 8.1 CLI Correctness

- Use the pinned v0.49.6 binary.
- Validate CLI flags against local help.
- Do not silently fall back to another Beads version.
- Never expose arbitrary shell execution through a Beads tool.
- Use the project working directory deliberately.
- Do not bypass Beads by manipulating its database directly.

### 8.2 JSON and Error Handling

- Parse native JSON when supported.
- Validate the minimum expected result shape.
- Preserve the generated task ID on creation.
- Distinguish an empty query result from a CLI failure.
- Report invalid IDs, unsupported flags, malformed JSON, and command timeouts explicitly.
- After ambiguous mutations, inspect the actual task state before retrying.

### 8.3 Context Efficiency

- Default to compact query results.
- Apply bounded result limits.
- Preserve the total count or truncation indication where reliably available.
- Keep full task details accessible through `bd_get`.
- Avoid returning full task history when only a list is requested.
- Do not silently truncate search results without signaling incomplete coverage.

### 8.4 Tool Discoverability

Use clear, short tool descriptions.

Register tools with `promptSnippet` and, where useful, concise `promptGuidelines` so the Research Lead knows which tool to call.

Examples:

```text
bd_query:
Search tasks by text and metadata filters.

bd_ready:
List tasks with no unsatisfied blocking dependencies.

bd_dependency:
Manage and inspect task relationships.

bd_comment:
Add or retrieve task-local progress notes.
```

Avoid verbose prompt instructions that repeat the whole guideline in the model context.

### 8.5 Scope and Permissions

These tools are intended primarily for the Research Lead host.

Do not automatically expose mutation tools to every subagent. The Research Lead should normally create and assign tasks, while children receive scoped assignment briefs.

Loading the extension is not a filesystem sandbox. Use Pi's effective tool allowlists and existing host-level permission controls.

---

## 9. Completion Checklist

The implementation is complete when the following tests pass:

- [ ] Beads v0.49.6 and SQLite backend verified.
- [ ] Pi extension loads successfully.
- [ ] `bd_create` creates tasks and returns IDs.
- [ ] `bd_get` retrieves exact tasks.
- [ ] `bd_query` supports text search and structured filters.
- [ ] `bd_update` changes fields and status.
- [ ] `bd_close` closes accepted tasks.
- [ ] `bd_ready` correctly identifies executable work.
- [ ] `bd_blocked` identifies dependency-blocked work.
- [ ] `bd_dependency` correctly manages blocking and provenance links.
- [ ] Epics and child tasks can be created and retrieved.
- [ ] Comments and labels work through their verified CLI operations.
- [ ] CLI failures produce explicit error results.
- [ ] Large results are bounded without silent information loss.
- [ ] Interrupted assignments remain recoverable.
- [ ] The end-to-end Research Lead workflow passes.

Optional advanced features, including stale-work detection, operational summaries, reopening, and atomic claiming, should be tested individually before activation.

## 10. Expected Deliverables

Produce:

```text
.pi/extensions/beads-tools/
├── index.ts
├── cli.ts
└── tests/
```

Along with:

- A short README explaining tool names, inputs, and installation.
- Tests for CLI behavior and Pi tool registration.
- Integration tests against a disposable Beads v0.49.6 database.
- A compact instruction snippet for the Research Lead explaining when to use the tools.

Do not add a separate database, a workflow engine, a scheduling service, or a dashboard.

The implementation should expose existing Beads capabilities with as little custom logic as practical.

**Final objective:** Enable the Research Lead to manage routine research work through reliable, efficient Pi tools while continuing to use Pi Subagents for execution and the existing project ledger for authoritative research and assignment state.# Guideline: Build Beads-Powered Pi Tools for Research Lead

**Target:** Pi Research Lead agent  
**Task-management backend:** Beads v0.49.6 (SQLite)  
**Implementation language:** TypeScript  
**Deliverable:** Project-local Pi extension exposing Beads CLI functionality as custom tools

## 1. Context and Purpose

The **Research Lead** is the main Pi agent responsible for autonomously conducting research projects. Its responsibilities include planning, investigation, task decomposition, delegation to subagents, implementation coordination, evaluation, analysis, and reporting.

To operate effectively over long-running research projects, the Research Lead needs a persistent, queryable task-management mechanism.

Without such a mechanism, the agent must repeatedly reconstruct its outstanding work, dependencies, assignments, and progress from conversation history or scattered project files. This increases context consumption and makes task coordination and session recovery unnecessarily difficult.

The objective is to provide the Research Lead with local task-management capabilities through **custom Pi tools backed by Beads**.

These tools should allow the agent to:

- Organize research work into manageable tasks.
- Search and retrieve relevant work efficiently.
- Track task status, priority, dependencies, and ownership.
- Discover which tasks can be executed next.
- Maintain traceability between discovered problems and originating work.
- Coordinate assignments to subagents and monitor unfinished work.
- Resume task management after interruptions or new Pi sessions.

The implementation must remain lightweight. Beads already implements the underlying task-management logic, so the task is primarily to expose its useful CLI functionality through Pi's tool interface.

**Scope boundary:** These tools manage tasks and operational assignments. They do not replace `pi-subagents`, research-stage governance, Advisor review gates, or the existing project-state ledger.

## 2. Expected Capabilities (Requirements)

### 2.1 Mandatory: Task CRUD without Delete

The toolset must support the following operations:

| Operation | Required capability |
|---|---|
| CREATE | Create a task with title, description, type, priority, and available metadata |
| RETRIEVE by ID | Fetch a specific task using its unique identifier |
| RETRIEVE by query | Search tasks by text and filter by structured metadata |
| UPDATE | Modify an existing task's fields, assignment, or status |
| DELETE | Explicitly excluded |

Retrieval is particularly important.

The Research Lead must be able to ask questions such as:

- Find all unfinished tasks related to evaluation.
- Find tasks assigned to `engineering-worker`.
- Find high-priority tasks associated with the current research cycle.
- Find the exact task identified by a known ID.
- Find tasks completed previously to avoid repeated work.

**Text search and structured filtering must be combinable**, rather than requiring the agent to fetch every task and inspect results manually.

For the initial implementation, Beads' native lexical search is sufficient if tests demonstrate that it meets these use cases. Do not assume semantic search, relevance ranking, stemming, or SQLite FTS5 unless verified.

### 2.2 Required: Assignment Management

The Research Lead must be able to:

1. Create work items suitable for delegation.
2. Assign an item to a designated subagent.
3. Identify assigned, unassigned, unfinished, and completed work.
4. Track execution progress and record blockers.
5. Find work requiring reassignment or recovery.
6. Close tasks when the Lead has accepted the deliverable.

A Beads task and a Pi execution run are different things.

For example, task `bd-abc` may correspond to assignment `WORK-014`, which may be attempted through more than one Pi subagent run.

Beads should contain the operational task record. The existing research project ledger continues to preserve authoritative assignment attempts, Pi run IDs, verification evidence, and acceptance decisions.

The Pi tools should facilitate this workflow without creating another delegation engine.

### 2.3 Required: Agent-Friendly Operation

Every tool should provide:

- Strongly typed input parameters.
- Structured, machine-readable output.
- Explicit error handling.
- Concise results suitable for an LLM context window.
- No requirement for the Research Lead to construct shell commands.
- Deterministic CLI invocation.
- Durable task storage across Pi sessions.

Do not expose a generic `bd_execute(command: string)` tool. Implement semantic wrappers instead.

### 2.4 Advanced Capabilities That Add Productivity

Besides basic CRUD, prioritize:

| Capability | Research Lead benefit |
|---|---|
| Task dependencies | Understand prerequisite work and execution order |
| Ready-work discovery | Find tasks that are no longer dependency-blocked |
| Blocked-work discovery | Identify scheduling bottlenecks |
| Epics and subtasks | Decompose larger research objectives |
| `discovered-from` relationships | Preserve provenance of unexpectedly discovered work |
| Task labels and priorities | Organize and prioritize the backlog |
| Comments and notes | Record concise task-local progress and blockers |
| Stale-work detection | Find tasks that may need inspection |
| Statistics and summaries | Obtain a quick operational overview |
| Atomic task claiming | Optional future support for concurrent autonomous workers |

These features should be exposed incrementally, starting with dependency-aware work discovery.

---

## 3. Beads v0.49.6 Overview

**Beads** is a local, agent-oriented issue/task tracker accessed through the `bd` command-line interface.

Relevant properties of the selected v0.49.6 release:

- Local installation.
- SQLite-capable storage.
- CLI-based task operations.
- JSON output for programmatic integration.
- Persistent issue identifiers.
- Task metadata and status.
- Dependencies and relationships between tasks.
- Ready-work discovery.
- Agent-oriented issue tracking.

Version v0.49.6 is deliberately pinned. Do not install or use the latest version when implementing this integration, since newer releases have materially different storage and command surfaces.

### 3.1 Reference Documentation

Use these sources:

1. [Beads v0.49.6 README](https://github.com/gastownhall/beads/blob/v0.49.6/README.md)
2. [Beads v0.49.6 CLI Reference](https://github.com/gastownhall/beads/blob/v0.49.6/docs/CLI_REFERENCE.md)
3. [Pi Extensions — Custom Tools](https://docs.pi.dev/latest/extensions#custom-tools)

The first two sources define the intended Beads version. The third defines how custom Pi tools must be registered and executed.

**Important verification instruction:** The pinned GitHub files were not directly accessible during preparation of this guide. Treat the CLI mapping below as the implementation checklist, not proof that every flag has been verified. Inspect the exact v0.49.6 binary and its local help before coding. Do not borrow undocumented commands or flags from newer Beads releases.

### 3.2 Verify the Local Beads Installation

From the research repository root, run:

```bash
bd version
bd --help
bd create --help
bd show --help
bd list --help
bd search --help
bd update --help
bd close --help
bd ready --help
bd blocked --help
bd dep --help
bd dep add --help
```

Also inspect the relevant optional commands:

```bash
bd comments --help
bd label --help
bd stale --help
bd status --help
bd reopen --help
```

The installed version must be **v0.49.6**.

Verify the active project uses the intended local SQLite backend. Do not run a database initialization command against a valuable existing workspace merely to test the integration.

Record any difference between the pinned documentation, the help output, and the commands proposed below. The verified executable takes precedence for actual behavior.

---

## 4. Functional Parity: Requirements vs. Beads CLI

The integration should primarily wrap existing Beads operations, not reimplement them.

### 4.1 Core Functional Parity

| Requirement | Beads CLI | Pi tool to implement |
|---|---|---|
| Create task | `bd create` | `bd_create` |
| Retrieve task by ID | `bd show` | `bd_get` |
| Search by text | `bd search` | `bd_query` |
| Filter by metadata | `bd list`, `bd search` | `bd_query` |
| Update task | `bd update` | `bd_update` |
| Close completed task | `bd close` | `bd_close` |
| Reopen task | `bd reopen` | `bd_reopen` (optional) |

**Assessment:** The documented Beads command family covers the mandatory requirements at the operation level.

The implementation must still verify which text fields are searched, how filters combine, how JSON is shaped, and how closed tasks are included.

### 4.2 Advanced Functional Parity

| Advanced requirement | Beads capability | Proposed tool |
|---|---|---|
| Retrieve executable tasks | `bd ready` | `bd_ready` |
| Retrieve dependency-blocked tasks | `bd blocked` | `bd_blocked` |
| Create dependencies | `bd dep add` | `bd_dependency` |
| Inspect dependency relationships | `bd dep list`, `bd dep tree` | `bd_dependency` |
| Remove incorrect dependency | `bd dep remove` | `bd_dependency` |
| Create epics/subtasks | `bd create` with hierarchy options | `bd_create` |
| Preserve discovered-work provenance | `discovered-from` relationship | `bd_dependency` |
| Assign a task | `bd update --assignee` | `bd_update` |
| Add progress comments | `bd comments` command family | `bd_comment` |
| Apply labels | `bd label` command family | `bd_label` |
| Identify stale tasks | `bd stale` | `bd_stale` |
| Review task statistics | `bd status` | `bd_status` |

The exact flags and JSON availability for the advanced commands are subject to the v0.49.6 verification step.

### 4.3 Capabilities Beads Does Not Replace

Some responsibilities cannot be implemented simply by wrapping Beads:

| Capability | Existing mechanism |
|---|---|
| Launch a subagent | Pi `subagent` tool |
| Retrieve Pi run/session status | Pi Subagents runtime |
| Verify work-package acceptance criteria | Research Lead |
| Store authoritative assignment attempts | Research project ledger |
| Enforce PLAN_GATE/CYCLE_GATE/REPORT_GATE | Existing research governance |
| Approve research-stage transitions | Research Lead plus required Advisor verdict |

Do not implement these inside the Beads extension.

The assignment workflow will use Beads tools alongside the existing mechanisms.

---

## 5. Implement the Pi Custom Tools

### Step 1 — Understand the Pi Extension API

Pi supports project-local TypeScript extensions.

A custom tool is registered using:

```typescript
pi.registerTool({
  name: "...",
  label: "...",
  description: "...",
  parameters: ...,
  async execute(toolCallId, params, signal, onUpdate, ctx) {
    // Implementation
  },
});
```

The important elements are:

- `name`: the tool identifier visible to the model.
- `description`: explains when and why the tool should be used.
- `parameters`: JSON Schema-compatible input definition.
- `execute`: implements the operation.
- `content`: human/model-readable tool result.
- `details`: structured result information.

Use TypeBox for parameter schemas.

For CLI execution, prefer `pi.exec()` because it supports argument arrays, explicit working directories, cancellation, and timeouts without introducing a shell.

### Step 2 — Create the Project-Local Extension

Use this location:

```text
.pi/
└── extensions/
    └── beads-tools/
        ├── index.ts
        ├── cli.ts
        └── tests/
```

`index.ts` registers Pi tools. `cli.ts` contains the shared Beads CLI execution helper.

Keep this implementation independent of the Research Lead's prompt file.

Project-local extensions are discovered by Pi when the project is trusted. During development, an extension can also be loaded explicitly with:

```bash
pi -e .pi/extensions/beads-tools/index.ts
```

### Step 3 — Implement a Shared Beads CLI Executor

Create `cli.ts`:

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export function createBeadsClient(pi: ExtensionAPI) {
  async function execute(
    args: string[],
    cwd: string,
    signal?: AbortSignal
  ): Promise<string> {
    const result = await pi.exec("bd", args, {
      cwd,
      signal,
      timeout: 15000,
      maxBuffer: 2 * 1024 * 1024,
    });

    if (
      result.code !== 0 ||
      result.killed ||
      result.truncated
    ) {
      throw new Error(
        `Beads command failed: ${result.stderr || result.stdout}`
      );
    }

    return result.stdout.trim();
  }

  async function json(
    args: string[],
    cwd: string,
    signal?: AbortSignal
  ): Promise<unknown> {
    const output = await execute(
      [...args, "--json"],
      cwd,
      signal
    );

    try {
      return JSON.parse(output);
    } catch {
      throw new Error(
        "Invalid JSON returned by Beads"
      );
    }
  }

  return { execute, json };
}
```

**Implementation requirements:**

- Never interpolate untrusted values into shell command strings.
- Pass CLI parameters as separate arguments.
- Use the current, approved project workspace.
- Check exit codes, termination, and truncated output.
- Preserve cancellation.
- Parse JSON only for commands whose `--json` support has been verified.
- Never interpret a failed command as an empty successful result.
- Do not access SQLite directly.

For mutations where the CLI returns plain text, execute the command and retrieve the resulting task through `bd show --json` when appropriate.

### Step 4 — Implement `bd_create`

**Purpose:** Create tasks, epics, and subtasks.

Expected arguments:

- `title`: required.
- `description`: optional for general tasks; expected for delegated work.
- `type`: defaults to `task`.
- `priority`: defaults to 2.
- `assignee`: optional.
- `parent`: optional.
- `labels`: optional.

Representative Beads command:

```bash
bd create "Implement retrieval benchmark" \
  --description "Implement baseline and evaluation runner" \
  --type task \
  --priority 2 \
  --json
```

Example Pi registration in `index.ts`:

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { createBeadsClient } from "./cli.js";

export default function (pi: ExtensionAPI) {
  const bd = createBeadsClient(pi);

  pi.registerTool({
    name: "bd_create",
    label: "Create Beads Task",
    description:
      "Create a persistent task or epic for research work.",
    parameters: Type.Object({
      title: Type.String({ minLength: 1 }),
      description: Type.Optional(Type.String()),
      type: Type.Optional(
        Type.Union([
          Type.Literal("task"),
          Type.Literal("epic"),
          Type.Literal("bug"),
          Type.Literal("feature"),
        ])
      ),
      priority: Type.Optional(
        Type.Integer({ minimum: 0, maximum: 4 })
      ),
      parent: Type.Optional(Type.String()),
    }),

    async execute(_id, params, signal, _update, ctx) {
      const args = [
        "create",
        params.title,
        "--type", params.type ?? "task",
        "--priority", String(params.priority ?? 2),
      ];

      if (params.description !== undefined) {
        args.push("--description", params.description);
      }

      if (params.parent !== undefined) {
        args.push("--parent", params.parent);
      }

      const data = await bd.json(args, ctx.cwd, signal);

      return {
        content: [{
          type: "text",
          text: JSON.stringify(data),
        }],
        details: { data },
      };
    },
  });
}
```

This is the reference implementation pattern for the remaining tools.

Add `assignee` and `labels` once their exact flags have been verified.

**Acceptance test:** Create a task and confirm its returned ID can be retrieved by `bd show`.

### Step 5 — Implement `bd_get`

**Purpose:** Retrieve one task by ID.

CLI:

```bash
bd show <task-id> --json
```

Schema:

```typescript
Type.Object({
  task_id: Type.String({ minLength: 1 }),
})
```

The implementation should call:

```typescript
bd.json(
  ["show", params.task_id],
  ctx.cwd,
  signal
)
```

Return the task's native fields in a normalized object, preserving unknown or optional metadata when possible.

Do not discard dependency information that may be relevant to the Research Lead.

**Acceptance test:** Retrieve a known task and verify its ID, status, description, priority, and assignee.

### Step 6 — Implement `bd_query`

**Purpose:** Support text search and structured filtering.

Use one unified Pi tool instead of making the Research Lead choose between `bd list` and `bd search`.

Recommended inputs:

```typescript
{
  text?: string;
  status?: string;
  type?: string;
  assignee?: string;
  priority?: number;
  label?: string;
  limit?: number;
}
```

Dispatch logic:

- If a text query is supplied, use `bd search`.
- Otherwise, use `bd list`.
- Append only CLI-supported filter flags.
- Default to a bounded result count, such as 20.
- Preserve support for including closed tasks.
- Return compact issue summaries rather than full descriptions.

Example:

```bash
bd search "evaluation" --status open --json

bd list --assignee engineering-worker --json
```

Verify that combining text and metadata filters applies the intended AND semantics. Test case sensitivity, searched fields, and empty-query behavior.

**Crucial:** Do not implement hidden post-filtering that silently loses matches because Beads returned only a limited candidate set.

Return metadata indicating when results may be incomplete.

### Step 7 — Implement `bd_update`

**Purpose:** Update existing task fields and operational status.

Recommended inputs:

```typescript
{
  task_id: string;
  title?: string;
  description?: string;
  priority?: number;
  assignee?: string;
  status?: string;
  notes?: string;
}
```

Build the CLI argument array using only fields explicitly supplied.

Examples:

```bash
bd update <task-id> \
  --assignee engineering-worker \
  --json

bd update <task-id> \
  --status in_progress \
  --json

bd update <task-id> \
  --priority 1 \
  --json
```

Verify valid status values against the pinned CLI.

Avoid using this tool to perform task closure. Provide `bd_close` for the completion operation.

After updating, retrieve the task if needed to confirm its actual state.

### Step 8 — Implement `bd_close` and Optional `bd_reopen`

**Purpose:** Complete accepted work and reopen tasks when necessary.

CLI:

```bash
bd close <task-id>
bd reopen <task-id>
```

Check whether the selected release supports JSON for these commands. If not, inspect their exit status and retrieve the task afterward.

The Research Lead must verify work before closure.

A successful Pi subagent run alone does not satisfy this condition. The existing assignment-acceptance record remains authoritative.

`bd_reopen` is useful for correcting premature closure or responding to invalidated work, but it can be deferred until needed.

### Step 9 — Implement `bd_ready` and `bd_blocked`

These are among the most valuable tools for routine autonomous research.

CLI:

```bash
bd ready --json
bd blocked --json
```

The tools should support optional priority, assignee, and result-limit filters when available.

**`bd_ready`** returns candidate tasks whose task-level blocking dependencies have been satisfied.

**`bd_blocked`** returns tasks blocked by dependencies, including their blocker relationships when available.

Prefer concise output:

```json
{
  "tasks": [
    {
      "id": "bd-example",
      "title": "Implement baseline",
      "priority": 1,
      "status": "open"
    }
  ],
  "truncated": false
}
```

Do not interpret `bd ready` as approval to dispatch work. The Research Lead must still check the relevant research-stage approval, readiness assessment, permissions, and budget.

### Step 10 — Implement `bd_dependency`

**Purpose:** Create, remove, and inspect dependencies and provenance relationships.

Use an action parameter:

- `add`
- `remove`
- `list`
- `tree`

CLI operations:

```bash
bd dep add <task-id> <prerequisite-id>

bd dep add <task-id> <origin-id> \
  --type discovered-from

bd dep list <task-id>

bd dep tree <task-id>
```

Verify exact argument direction and accepted dependency types against v0.49.6.

Support at least:

- `blocks`: work ordering.
- `discovered-from`: origin/provenance of newly discovered tasks.

Where supported and appropriate, expose additional relationship types without introducing a new graph model.

Do not treat parent-child hierarchy as a blocking dependency unless explicitly required by Beads' verified semantics.

Tests must establish that:

- A prerequisite prevents dependent work from appearing ready.
- Closing the prerequisite makes the dependent work eligible.
- A `discovered-from` relationship does not itself block execution.
- Invalid or cyclic blocking relationships are rejected.

### Step 11 — Implement `bd_comment` and `bd_label`

These tools provide task-local annotation and organization.

For `bd_comment`, wrap the verified v0.49.6 `bd comments` add/list operations.

Typical comments include:

- Implementation progress.
- An encountered blocker.
- A concise result summary.
- A reference to the Pi assignment or run.
- A reason for reopening work.

For `bd_label`, wrap the verified label add/remove/list operations.

Possible labels include:

```text
research-cycle-1
implementation
evaluation
high-risk
needs-review
```

Do not invent a large mandatory label taxonomy. Begin with labels that the Research Lead actually uses for retrieval and filtering.

Store references and concise task-local information in Beads; keep full research evidence in the project workspace.

---

## 6. Add Advanced Productivity Features

After the core tools work, add the following capabilities in the suggested order.

### 6.1 Epics and Subtasks

Extend `bd_create` to support hierarchy via the pinned release's parent option.

Example:

```text
Epic: Evaluate New Retrieval Approach
├── Prepare benchmark dataset
├── Implement baseline
├── Implement proposed retrieval method
├── Run evaluation
└── Analyze results
```

Use this to represent bounded work packages within a research objective.

The Research Lead should create children when decomposition provides better delegation, dependency management, or progress visibility—not mechanically for every trivial action.

### 6.2 Discovered-Work Tracking

When research uncovers new work, the Lead should create a new task and link its origin through `discovered-from`.

For example:

```text
Original task:
Run retrieval benchmark

Discovered task:
Investigate anomalous evaluation scores
```

This preserves provenance and supports later analysis of unexpected research findings.

The Lead should not automatically execute every discovered task. It must evaluate the task's relevance, priority, scope, and authorization.

### 6.3 Stale Task Detection

Implement `bd_stale` using the pinned CLI's supported stale-work command and flags.

Use it to find tasks with no recent recorded activity.

Treat the results as **inspection candidates**, not evidence that a worker has failed or a task has been abandoned.

Cross-check with Pi run status before retrying or reassigning work.

### 6.4 Operational Summary

Implement `bd_status` over the CLI's status/statistics capability.

The goal is to answer routine questions such as:

- How much work remains open?
- What is currently in progress?
- What work is blocked?
- How much work has been completed?

Use concise, structured output.

Avoid generating a separate dashboard or maintaining duplicate statistics if the CLI already computes them.

### 6.5 Atomic Claiming — Optional

If v0.49.6 supports atomic claiming through `bd update --claim`, consider exposing it only when multiple authorized agents can independently select work from a shared queue.

For the initial Research Lead architecture, **prefer explicit Lead-controlled assignment**.

Automatic claiming is unnecessary while the Lead is the sole dispatcher, and it must never bypass fixed-role assignment rules.

### 6.6 Persistence and Synchronization

If Beads' export or synchronization operations are required by the research environment, verify and expose only the necessary operations.

Do not make synchronization an implicit side effect of every model-facing tool.

The existing Git checkpoints, artifact manifests, and research project state must remain consistent with any exported or synchronized task data.

---

## 7. Validate the Integration Through a Realistic Workflow

Use a disposable research project.

### Scenario: Implement and Evaluate a Research Method

**1. Create a research epic.**

Use `bd_create` to create an epic representing the evaluation objective.

**2. Create child tasks.**

Create tasks for:

- Dataset preparation.
- Baseline implementation.
- Proposed method implementation.
- Evaluation execution.
- Results analysis.

**3. Establish execution dependencies.**

Use `bd_dependency` so the evaluation task depends on the necessary implementations and dataset.

**4. Query available work.**

Call `bd_ready`.

Confirm that dependent evaluation tasks are not returned prematurely.

**5. Prepare a real assignment.**

The Lead assesses task readiness, selects the eligible subagent, and records the work package and assignment attempt in the existing project ledger.

Use `bd_update` to record operational ownership.

**6. Delegate through Pi Subagents.**

The Lead calls `subagent` directly, passing the assigned specification.

Record the returned Pi run/session references through the existing assignment-tracking mechanism.

**7. Track progress.**

Use `bd_update` and `bd_comment` to record operational changes.

**8. Verify completion.**

The Lead inspects the returned evidence and records acceptance or rejection.

On acceptance, call `bd_close`.

**9. Query new ready work.**

Call `bd_ready` again.

Confirm that completing prerequisites unlocks dependent tasks.

**10. Simulate a session interruption.**

Start a new Research Lead session.

Use `bd_query`, `bd_get`, `bd_ready`, and `bd_blocked` to reconstruct the operational backlog.

Reconcile the actual Pi run status and authoritative assignment records before continuing.

This scenario is the primary end-to-end acceptance test.

---

## 8. Engineering Quality Requirements

The wrapper implementation should follow these practical rules.

### 8.1 CLI Correctness

- Use the pinned v0.49.6 binary.
- Validate CLI flags against local help.
- Do not silently fall back to another Beads version.
- Never expose arbitrary shell execution through a Beads tool.
- Use the project working directory deliberately.
- Do not bypass Beads by manipulating its database directly.

### 8.2 JSON and Error Handling

- Parse native JSON when supported.
- Validate the minimum expected result shape.
- Preserve the generated task ID on creation.
- Distinguish an empty query result from a CLI failure.
- Report invalid IDs, unsupported flags, malformed JSON, and command timeouts explicitly.
- After ambiguous mutations, inspect the actual task state before retrying.

### 8.3 Context Efficiency

- Default to compact query results.
- Apply bounded result limits.
- Preserve the total count or truncation indication where reliably available.
- Keep full task details accessible through `bd_get`.
- Avoid returning full task history when only a list is requested.
- Do not silently truncate search results without signaling incomplete coverage.

### 8.4 Tool Discoverability

Use clear, short tool descriptions.

Register tools with `promptSnippet` and, where useful, concise `promptGuidelines` so the Research Lead knows which tool to call.

Examples:

```text
bd_query:
Search tasks by text and metadata filters.

bd_ready:
List tasks with no unsatisfied blocking dependencies.

bd_dependency:
Manage and inspect task relationships.

bd_comment:
Add or retrieve task-local progress notes.
```

Avoid verbose prompt instructions that repeat the whole guideline in the model context.

### 8.5 Scope and Permissions

These tools are intended primarily for the Research Lead host.

Do not automatically expose mutation tools to every subagent. The Research Lead should normally create and assign tasks, while children receive scoped assignment briefs.

Loading the extension is not a filesystem sandbox. Use Pi's effective tool allowlists and existing host-level permission controls.

---

## 9. Completion Checklist

The implementation is complete when the following tests pass:

- [ ] Beads v0.49.6 and SQLite backend verified.
- [ ] Pi extension loads successfully.
- [ ] `bd_create` creates tasks and returns IDs.
- [ ] `bd_get` retrieves exact tasks.
- [ ] `bd_query` supports text search and structured filters.
- [ ] `bd_update` changes fields and status.
- [ ] `bd_close` closes accepted tasks.
- [ ] `bd_ready` correctly identifies executable work.
- [ ] `bd_blocked` identifies dependency-blocked work.
- [ ] `bd_dependency` correctly manages blocking and provenance links.
- [ ] Epics and child tasks can be created and retrieved.
- [ ] Comments and labels work through their verified CLI operations.
- [ ] CLI failures produce explicit error results.
- [ ] Large results are bounded without silent information loss.
- [ ] Interrupted assignments remain recoverable.
- [ ] The end-to-end Research Lead workflow passes.

Optional advanced features, including stale-work detection, operational summaries, reopening, and atomic claiming, should be tested individually before activation.

## 10. Expected Deliverables

Produce:

```text
.pi/extensions/beads-tools/
├── index.ts
├── cli.ts
└── tests/
```

Along with:

- A short README explaining tool names, inputs, and installation.
- Tests for CLI behavior and Pi tool registration.
- Integration tests against a disposable Beads v0.49.6 database.
- A compact instruction snippet for the Research Lead explaining when to use the tools.

Do not add a separate database, a workflow engine, a scheduling service, or a dashboard.

The implementation should expose existing Beads capabilities with as little custom logic as practical.

**Final objective:** Enable the Research Lead to manage routine research work through reliable, efficient Pi tools while continuing to use Pi Subagents for execution and the existing project ledger for authoritative research and assignment state.