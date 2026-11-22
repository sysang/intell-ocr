# research-ops — deterministic orchestration toolset (blueprint §10.7)

Stdlib-only Python. No installs, no network.

- `ledger.py` — project live-ledger CLI: `validate | status | next |
  progress | termination-check | show <section> | advance --event ...`.
  Exit 0 ok, 1 invariant violation / refused event, 2 usage error.
  Implemented ledger subcommands: `get` (via `show`), `advance`,
  `termination-check`, `status`, `next`, `progress`.
- `project-state.schema.json` — canonical schema for `project-state.json`
  (blueprint §8.8). Validation is implemented natively in `ledger.py`.
- `test_ledger.py` — 16 self-tests against fixture ledgers
  (`python3 test_ledger.py`).

Not yet built (spec'd in §10.7): `validate-verdict`,
`verdict-still-covers`, `okf-gate-precheck`, `preflight`,
`freshness-flags`, `smoke-roster`.
