# Design: fix --only check order

Revised after the panel (see panel.md). Finding ids are given in brackets.

## Decisions

1. **Resolve the change up front, always.** `main()` calls `check_change(ctx)` once, before the
   loop, and stores `(status, msg)`. It replaces the conditional pre-call. [A-M3]
2. **A change failure is never swallowed where it matters.** If the stored status is FAIL and
   `change` or any `NEEDS_CHANGE` check was requested, it counts toward the exit code. If
   `change` itself wasn't requested, it is printed first anyway. Runs that need no change
   context, such as `release.yml`'s `--only build`, are unaffected: a shallow tag checkout has no
   base, so every archived change looks in flight and `change` fails there by design. [F-M1, A-M1, self-check]
3. **Dependents don't run on a half-set context.** After a `change` FAIL, the checks in
   `NEEDS_CHANGE` = {risk-floor, approval, panel, tasks, evidence, artifacts-first} print
   `SKIP  <name>  blocked: change failed`. The run still exits 1 because of 2. This removes the
   AttributeError in `check_approval` when a PR body says tier 1-2 but there is no change dir. [F-m1, F-m3]
4. **Clean `--only` input.** Names are split on commas, trimmed, and de-duplicated in order.
   An unknown name, or an empty list, exits 2 with `unknown check: <name>` and the valid names.
   [A-M2, A-m2]

Alternative considered: reorder `names` so `change` comes first. It changes the output order the
caller asked for, and doesn't address a swallowed FAIL. Rejected. [S-m5]

## Assumptions

| Assumption | Command | Observed |
| --- | --- | --- |
| Only `check_change` sets `ctx.tier` and `ctx.change_dir` | `grep -n "ctx.tier = \|ctx.change_dir = " scripts/lib/check_change.py` | Lines 153, 158, 163, 165, all inside `check_change` |
| `check_change` has no side effects besides ctx, and is idempotent | read `check_change` | Reads proposal.md and the PR body only; no git calls |
| Only release.yml uses `--only`, and only for `build` | `grep -n -- --only .github/workflows/*.yml .pre-commit-config.yaml .claude/hooks/*.sh` | `release.yml:29: scripts/check-change.sh --only build`; everything else uses `--stage`, whose lists put `change` first |
| The bug reproduces | on this branch: `scripts/check-change.sh --only approval,panel,change` | `SKIP approval tier 0`, `SKIP panel no change`, `PASS change tier 2` |
| Unknown names crash | `scripts/check-change.sh --only bogus` | `KeyError: 'bogus'` |
