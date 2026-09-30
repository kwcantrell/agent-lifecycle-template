# Grandfather in-flight changes

Tier: 2
Tier reason: touches scripts/ and openspec/config.yaml (high-risk paths); adds a gate exemption.

Approved-by: Kalen 2026-09-29

## Why

A repo adopting the lifecycle usually has changes already in flight that predate it. infisical's
`self-host-infisical` has no `Tier:` line, a prose panel and a 2,000-line branch, so every gate
fails and the change can't be finished under the lifecycle. The first design (safe-adoption)
auto-grandfathered with no bounds, and its panel found three holes:
- the waiver never expires;
- a later change reusing the id inherits it;
- the checker fails a change with no `Tier:` before any grandfather rule could run.

That change was split. This part is the checker only; the installer's adoption path follows as its
own change.

## What Changes

- **A new list, read from the base only.** `lifecycle.grandfathered_changes` is a list of change
  ids a human adds by hand in its own PR. It is read only from the merge-base's config, never
  from the PR. The value is normalized: anything that isn't a list of strings counts as empty.
- **Two conditions to qualify.** A change is grandfathered only if its id is listed **and**
  `openspec/changes/<id>/` exists on the merge-base. Once the archive PR merges, the entry stops
  matching.
- **No two-step backdoor.** A change directory declared tier 0 fails, since tier 0 needs no
  change. Any change folder that reaches main has had human approval.
- **Archive PRs are recognized:** `archive/YYYY-MM-DD-<id>` matches `<id>`.
- **What a grandfathered change gets:**
  - `change` reports WARN, and the change-dependent checks and `size` report SKIP.
  - `risk-floor` reports WARN, listing the high-risk paths touched, instead of skipping.
  - In CI the PR body must say `Grandfathered: <id>`, so the waiver shows in the PR.
  - Every other gate still runs.
- **A hint when it doesn't apply.** If a change is listed but not grandfathered, the failure says
  why (not on the merge-base: merge main).
- **Docs:** an ADR, `docs/lifecycle.md` (check table and how to grandfather), and known gaps in
  `docs/security.md`.

## Non-goals

- The installer's adoption path (conflict report, settings merge, rulebook link), which is change A2.
- Auto-filling the list. A human decides what is grandfathered.

## Depends on

- `accurate-gates` (PR #3), for the base-branch exemption reading this extends.

## Impact

- `scripts/lib/check_change.py` (about 60 lines), `openspec/config.yaml`, `tests/`,
  `docs/decisions/0014-grandfathered-changes.md`, `docs/lifecycle.md`, `docs/security.md`.
