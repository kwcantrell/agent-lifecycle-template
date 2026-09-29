# Fix --only check order

Tier: 2
Tier reason: touches scripts/ (high-risk path); the gate checker is the lifecycle's enforcement.

Approved-by: Kalen 2026-09-29

## Why

`scripts/check-change.sh --only approval,panel,change` reports `SKIP approval: tier 0` and
`SKIP panel: no change` on a tier 2 change. `approval`, `panel`, `tasks`, `evidence`,
`artifacts-first` and `risk-floor` read the tier and change directory that `change` sets. Under
`--only`, `change` runs in the order listed, so any of those checks listed before it sees no
change. Main's full run and CI are unaffected: their stage lists put `change` first. But a
human or agent running a subset can get a false SKIP and believe a gate passed.

## What Changes

- The checker resolves the change and tier once, before any check runs, whatever order
  `--only` lists them in.
- A failing `change` result always counts toward the exit code. It is printed even when
  `change` isn't in `--only`, so a subset run can't swallow it.
- When `change` fails, checks that depend on it (`risk-floor`, `approval`, `panel`, `tasks`,
  `evidence`, `artifacts-first`) report `SKIP ... blocked: change failed` instead of running on a
  half-set context. This also fixes a crash: `Tier: 1` in a PR body with no change directory
  made `approval` raise AttributeError.
- `--only` names are trimmed and de-duplicated. An unknown or empty name is an error (exit 2)
  instead of a traceback, or a silent fallback to the full stage.
- Regression tests cover each of the above.

## Non-goals

- Changing any check's logic, beyond not running dependents after a `change` failure.
- Changing the stage lists.

## Impact

- `scripts/lib/check_change.py` (about 25 lines), `tests/test_check_change.py`, a new
  `openspec/specs/gate-checker/spec.md` on archive.
