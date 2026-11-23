# research-ops — deterministic orchestration toolset (blueprint §10.7)

Stdlib-only Python. No installs, no network.

- `ledger.py` — project live-ledger CLI: `validate | status | next |
  progress | termination-check | show <section> | advance --event ...`.
  Exit 0 ok, 1 invariant violation / refused event, 2 usage error.
  `show` reads a whole project-state section, not one task or evidence record.
- `project-state.schema.json` — canonical schema for `project-state.json`
  (blueprint §8.8). Validation is implemented natively in `ledger.py`.
- `test_ledger.py` — self-tests against fixture ledgers (`python3 test_ledger.py`).

[Blueprint §8.9](../../blueprint-v1.md#89-assignment-ledger-and-delegation-lifecycle) adopts **Beads v0.49.6 (SQLite)** for task lookup, search, assignment, and dependencies. This Python tool remains the project lifecycle prototype; `assignments` is a legacy one-run shape, not the planned execution-evidence model. The Pi Beads extension, project binding and close guard, and exact historical evidence operations are not implemented here.

Verified directly on v0.49.6 in a disposable SQLite repository: `search --query` combines text with `--assignee`, `--label`, `--status`, and `--priority-max`; `show` retrieves a closed task by ID; `ready` excludes work with a blocking dependency and includes it when the dependency closes. `list` omits closed tasks by default; `list --all` includes them. In the fixture, `search` without `--status` included closed matches. This verifies native CLI behavior, not Pi tool confinement or evidence/close reconciliation.

Not yet built (spec'd in §10.7): `validate-verdict`,
`verdict-still-covers`, `okf-gate-precheck`, `preflight`,
`freshness-flags`, `smoke-roster`.
