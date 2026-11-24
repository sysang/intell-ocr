# Research operations

[Blueprint §8.9](../../blueprint-v1.md#89-assignment-ledger-and-delegation-lifecycle) is authoritative. This is a Lead-invoked toolset, not a scheduler. Beads runs the backlog; the project ledger runs no agents and stores no duplicate task graph. The Lead calls the pinned `pi-subagents` runtime directly.

## Start a project

From the repository root, with Python 3.10+, Node 24, Git, Pi 1.6.0, `pi-subagents` 0.89.2, and `bd` 0.49.6 installed:

```sh
python3 -B tools/research-ops/research.py init pilot \
  --question 'Does method B improve the frozen evaluation metric over A?' \
  --objective 'Compare A and B on a held-out set with paired observations'
python3 -B tools/research-ops/research.py preflight pilot
python3 -B tools/research-ops/research.py lead pilot --model 'provider/model'  # replace with your pinned model
```

The project receives its own `.beads/beads.db`, local `research-config.json`, managed `project-state.json`, and artifact tree. Init refuses an existing project directory; it never imports a root/child database. If interrupted during init, inspect the incomplete project before replacing or recovering it. Keep `.beads`, lock files, local machine paths, and secrets out of Git. Version evidence artifacts and the ledger. Back up the bound SQLite database separately using a consistent SQLite backup; do not copy only the live `.db` file out from under an active writer.

The default launcher starts **planning-only** Pi using built-in tools and the explicit Beads extension; child delegation and MCP are not loaded. Use a model available without extra provider extensions in that mode. For a qualifying deployment, `--enable-delegation` requires the operator attestation described below. `--resume <pi-session-path-or-id>` changes only the conversation: reload the bound project ledger and reconcile before new work. Do not run multiple Lead host sessions against the same project. This repository tracks `.pi/` in a separate Git checkout; deploy both trees together.

## Beads tools inside the Lead session

- `bd_create`: supply an explicit full ID, title, and description. Use the prefix from `init`. If the receipt is lost, query that exact ID and compare fields before trying another mutation.
- `bd_get`: full ID only, including closed tasks. `bd_query`: required status scope (`active`, `all`, or one status), optional text, assignee/type/labels/priority range, limit 1–100. Native lexical search, not historical or semantic search.
- `bd_ready` / `bd_blocked`: operational discovery only. `bd_dependency`: add/remove/list planned blocking edges; `id` is the dependent and `prerequisite` is the blocker. Removing an edge is a Lead decision, not a substitute for the actual evidence pin.
- `bd_update` changes live task metadata/status. `bd_close` needs an exact durable acceptance or optional drop record (`recordId`) and a reason. A dropped task cannot release a dependent. `bd_reopen` corrects operational status; it does not reauthorize evidence.

No task Delete or generic CLI passthrough. The extension uses a shell-free argument vector, explicit database path, direct SQLite, no daemon or JSONL sync, bounded process time/output, and `model-only` Pi exposure. This prevents indirect Pi tool calls through the normal callable-tool registry. It does not confine an unrestricted shell or untrusted extension. Do not expose raw `bd`, project ledger writes, or this database to children in a live deployment.

## Ledger operations

```sh
STATE=research-projects/pilot/project-state.json
python3 -B tools/research-ops/ledger.py status "$STATE"
python3 -B tools/research-ops/ledger.py apply "$STATE" lifecycle start-scoping \
  --input - --op-id scope-001 --expected-revision 0 \
  --actor research-lead --reason 'Begin charter review' <<<'{}'
python3 -B tools/research-ops/ledger.py get "$STATE" <exact-record-id>
```

`status`, `next`, `progress`, `termination-check`, and `show <section> <state>` are read-only views. A tool predicate or Candidate is not permission. Use `apply <state> <evidence|lifecycle> <action>` for managed writes. `--input` accepts a JSON file or `-` (stdin); each call needs the current revision and stable operation ID. An exact replay with the original parameters returns `replayed: true` and never permits launch. A changed operation with the same ID or a stale revision is refused. Legacy snapshots remain readable and their legacy `advance` only simulates a state; don't relabel legacy records as managed. Reconcile and import verified records explicitly before adopting existing projects.

### Evidence actions and payloads

| Action | Required payload and conditions |
|---|---|
| `issue` | `id` (revision ID), `assignment_id`, `beads_task_id`, one `assignee`, `mode` (`read`, `write`, `execute`), `scope`, `deliverable`, `criteria`, `exclusions`, pinned `source_versions` map, `read_paths`, `modify_paths`, `commands`, `external_actions`, `tools`, `attempt_limit`, `soft_seconds`, `hard_seconds`. Write/execute require full `base_revision` and commands or `verification_exemption`. Use `previous_revision` when revising and `routing_reason` for an approved pool member. |
| `pin-use` / `mark-ready` | Pin actual evidence by `id`, `consumer` (exact revision or review ID), `decision_id`, relative `output`, and `required` boolean. Readiness uses the revision `id` and recorded `basis`. |
| `reserve` | `id` (attempt), `revision_id`, `profile_ref` (operator-verified effective profile), and absolute `workspace` for write/execute. Recheck the linked Beads task and runtime resolution as Lead. Only the same uninterrupted call using the fresh receipt may submit once. |
| `attach-run`, `launch-unknown`, `prove-non-dispatch` | Attempt `id` and factual `evidence`; attach also needs the exact Pi `run_id`. If no reliable correlation exists after an interrupted submission, record `launch-unknown`; do not retry into uncertainty. |
| `hard-cutoff`, `observe-termination`, `record-no-result`, `reconcile-effects` | Attempt `id` and `evidence`. Record cutoff separately from termination. Reconcile effects only after observed termination; disposition is `clean`, `isolated`, or `integrated`. Termination means actual loss of mutation authority, not just a stop request. |
| `result` | `id`, echoed `assignment_id` / `revision_id` / `attempt_id`, `status`, `source_versions`, `deliverable`, `evidence_refs`, `gaps`. Write/execute add `affected_paths`, `deviations`, `follow_ups`, and `verification` keyed by the exact command with `{exit_code, output}` or `{not_run}`. Late results stay on the original attempt. |
| `decision` | `id`, `attempt_id`, `verdict` (`accepted` or `rejected`), `rationale`, exact `result_id` for acceptance, `supersedes` when correcting. Lead verifies independently. Unsupported, stale, partial, blocked, failed-check and late results cannot count as completion. |
| `record-availability` | `id`, `decision_id`, `artifacts` map (project-relative paths → SHA-256); write deliveries also need the integrated Git `checkpoint` containing those exact bytes. The adapter rechecks evidence before operational closure. |
| `drop-optional` | `id`, `revision_id`, `optional: true`, and recorded `gap`; all prior attempts must be reconciled. |

The ledger checks structural and causal consistency, Git ancestry and local hashes. It does **not** independently observe the Pi process, prove that a claimed check ran, choose a role, infer a dependency, or enforce filesystem/network boundaries. For an authorized dispatch, use the exact fresh `subagent` call with `context: "fresh"`, the verified `agent`, explicit model and `cwd` where applicable, an outer runtime limit, and the whole pinned brief including all three IDs. Preserve actual subagent receipts and status observations, not a reconstructed run reference. `complete`, child `SUCCESS`, Lead acceptance, integration, and Beads closure are distinct. If state disagrees with Beads, use exact IDs to reconcile and do not advance affected work. No cross-store transaction; don't issue another launch or blind close in response to a lost acknowledgment.

### Gate actions

Use `start-scoping`, `start-planning` (`charter_ref`), `begin-inner-attempt`, `objective` (`id`, `status`, `evidence_refs`), and `progress` (`verdict`, `credible_lever`, `evidence_refs`). Store Advisor/architect advice separately with `record-consultation` (`id`, `agent`, `run_id`, `status`, `evidence_ref`). Use `record-blocker` (`id`, `description`, `status`), `open-hold` (`reason`), `resolve-hold` (`resolution`), or `suspend-held` (`status_report` and confirmed blocker or `director_decision`) as applicable.

Create a phase-specific, versioned artifact manifest using `checks.py manifest` (relative file paths). `checks.py validate-verdict` and `checks.py verdict-still-covers` check shape, phase, target, and hashes. Supply exact review `id`, `gate`, `phase`, `advisor_run_id`, `manifest`, and §4.4 `verdict` JSON or `failure` to lifecycle `gate-review`. `gate-route` requires that review `id` and a legal `route`; a HOLD needs a reason and a terminal stop needs `status_report`. Use `withdraw-stale-review` for an unrouted review that no longer matches, then re-review. Protocol, readiness, complete/diagnosis-only exit, cycle, and report are distinct. `replan` requires `proposed_route: "replan"`, `next_plan`, and `replan_rationale` in the reviewed cycle manifest. Only consuming a current `approve/replan` charges the next cycle.

`checks.py okf-gate-precheck` invokes the existing OKF writer validator (install the writer's PyYAML requirement separately) and optional reader envelope validator, and reconciles local index links and created files. `checks.py freshness-flags` checks an explicitly extracted provenance snapshot against the ledger and `stale_after`; it does not infer freshness from Markdown prose. Validate gates and preserve these reports before relying on them. `analyze.py` is a reference paired-evaluation helper: version and freeze the config/input hashes, record raw `example_id,baseline,candidate` CSV, and emit JSON analysis or a Markdown **draft**, not a final report or Advisor verdict.

## Deployment exit checks (not satisfied by fixture tests)

`preflight` verifies installed pins, bindings, and file fingerprints, not actual role resolution. In a disposable, credentialed Pi deployment with the operator's approved provider and confinement setup:

1. Inspect `subagent({action:"list",options:{capabilities:true}})` for exact discovery; confirm the Lead isn't a child. Run each fixed role with explicit `fresh` context against trivial disposable inputs. Capture the actual run ID, definition source, requested and resolved provider/model, override source, executed tool list/reachable tools, and the final result. Keep actual output and inspection files in the project.
2. Probe denied paths, commands, delegation edges, `codemode` access, fresh-context exclusions, hard-cutoff process exit, and correlation of an exact prelaunch attempt after restart. Run the Worker writer pilot and interrupted-close recovery. Refuse release when any mandatory probe cannot be verified; an assertion of attempted dispatch is not proof. Run a separate approved read-only pool pilot; recheck actual pool profile and its full capabilities at every call. `checks.py check-pool-profile APPROVAL OBSERVATION` compares the operator's `{operator, profile}` approval to the actual observed resolution. A profile contains `name`, `definition_sha256`, exact `model`, `override_source`, and explicit `tools`, `indirect_tools`, and `model_endpoints` lists. This comparison is not discovery or sandbox enforcement. No default pool is authorized.
3. Save `runtime/attestation.json` with `operator`, `fingerprints` (from `preflight`), and `roles` keyed by the seven names. Each role includes `definition`, `run_id`, `requested_model` and `resolved_model` as exact `provider/model`, `override_source`, `completed: true`, `fresh_context: true`, `effective_tools`, and `artifacts` as a nonempty project-relative SHA-256 map. `probes` is a map from `writer_confinement`, `worker_nested_edges`, `codemode_boundary`, `exact_restart_correlation`, `hard_cutoff_and_process_exit`, and `fresh_context_and_models` to equivalent evidence maps. `smoke-roster <project>` **validates recorded observations; it does not run paid jobs or certify their truth.** Inspect the actual artifacts before attesting. Relaunch after material runtime changes only after re-verification.
4. Establish provider/API and compute quotas outside the local ledger, independent monitoring and interrupt authority, and retained runtime evidence. This toolset accounts for cycles, reviews and attempts, not external compute charges. For real scientific evaluation, the Director supplies the research question and approved resource budget; compare repeated runs and preserve negative/inconclusive findings.

## Local verification

```sh
python3 -B -m unittest discover -s tools/research-ops -p 'test_*.py'
node --test .pi/extensions/beads-tools/adapter.test.ts
```

Tests use disposable repositories. They include real Beads SQLite, a real Git checkpoint, and a credential-free Pi startup/exposure probe. Gate and child execution outcomes in fixtures are simulated; no live research, provider calls, or sandbox certification is implied. See [todos.md](../../todos.md) for milestone status.
