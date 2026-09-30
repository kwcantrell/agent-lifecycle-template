# Design: grandfather in-flight changes

Revised after the panel (see panel.md). Finding ids are given in brackets.

## Decisions

1. **Its own base read, never the PR's.** `base_grandfathered(base)` returns a list of strings.
   It returns `[]` in any of these cases [A-M1, A-M2, F-M3]:
   - `base` is falsy;
   - `git show <base>:openspec/config.yaml` fails;
   - the base has no `lifecycle` mapping;
   - the value isn't a list (for example a string, which would substring-match).

   Non-string items are dropped. It is not added to `EXEMPTION_KEYS`, whose fallback returns
   the PR's own config.
2. **Must exist on the merge-base.** `git cat-file -e <base>:openspec/changes/<id>`, with output
   captured; exit 0 means it exists. That gives four properties:
   - A change created after adoption isn't on the base, so it doesn't qualify.
   - After the archive PR merges, the directory is gone from the base, so the entry is dead.
   - A shallow clone has no base, so nothing qualifies (fails closed). [A-m1]
3. **Tier 0 can't carry a change.** `check_change` fails when a change directory declares
   `Tier: 0`, or a PR body says tier 0 over a change directory, with "tier 0 needs no OpenSpec
   change; use tier 1". A change folder therefore reaches main only through an approved tier 1-2
   PR, which closes the two-step route: merge a bare directory, then list it. [F-M1]
4. **Id from the path.** `openspec/changes/<id>` gives `<id>`. `openspec/changes/archive/<name>`
   gives `<name>` minus one leading `\d{4}-\d{2}-\d{2}-`. Archive support stays, because without it
   a grandfathered change fails every gate on its archive PR, so it could never finish.
   [S-M2 declined, see panel.md; A-m2]
5. **Order and outcome.** The one-change-per-branch FAIL still comes first. Then, if the change
   is grandfathered:
   - `ctx.grandfathered = True`, `ctx.change_dir` is set, and `ctx.tier = None`; a PR-body
     `Tier:` is ignored;
   - `change` returns WARN, "grandfathered: <id> predates the lifecycle";
   - in CI (a PR event is present), the PR body must contain `Grandfathered: <id>`, or `change`
     FAILs with "declare `Grandfathered: <id>` in the PR body". [F-m1 visibility]
6. **What changes per check.** In `main()`, the grandfathered branch is checked before the
   `change_failed` branch. [A-m3]
   - `approval`, `panel`, `tasks`, `evidence`, `artifacts-first` and `size` report
     `SKIP grandfathered`.
   - `risk-floor` reports WARN "grandfathered; high-risk paths touched: [...]", or PASS if none
     are touched. It no longer skips silently. [F-M2]
   - Every other check runs normally.
7. **Hint on near-misses.** When the `Tier:` FAIL fires and the change's id is in the working
   tree's `grandfathered_changes` but doesn't qualify, the message adds "(listed, but not
   grandfathered: the merge-base lacks it in its config or lacks the change dir; merge main)".
   [A-M3]
8. **Docs.**
   - ADR 0014: why grandfathering exists, its bounds, and when to retire it.
   - docs/lifecycle.md check-table rows `change`, `risk-floor` and `size`, plus a
     "Grandfathering" subsection: PR 1 lists the id (tier 2, since it touches config); the
     change branch merges main; its PR says `Grandfathered: <id>`. [S-m4]
   - config.yaml comment: "Changes in flight before adoption. Read from the merge-base only.
     Entries die when the change is archived."
   - docs/security.md known gaps: a grandfathered branch's scope is unbounded (no size cap);
     high-risk paths only WARN; any archive dir for a listed id qualifies while the base still
     has the id. Human review is the control. [F-m2, A-m2]

## Assumptions

| Assumption | Command | Observed |
| --- | --- | --- |
| infisical's in-flight change exists on its main | `git -C /home/spark/infisical ls-tree -d main openspec/changes/self-host-infisical` | tree entry present |
| It has no Tier line | `grep -c '^Tier' .../self-host-infisical/proposal.md` | `0` |
| infisical's main has no lifecycle block, so install and grandfathering are two PRs | `git -C /home/spark/infisical show main:openspec/config.yaml \| grep -c lifecycle` | `0` |
| `cat-file -e` tests existence | `git cat-file -e HEAD:openspec/specs; echo $?` / missing path | `0` / `128` plus stderr |
| An archive rename shows only the destination in the diff | panel repro: `git mv ... archive/2026-10-01-legacy; git diff --name-only $B` | only the archive path |
| The existing exemption fallback returns the PR's config | `git show accurate-gates:scripts/lib/check_change.py`, `with_base_exemptions` | `return cfg` on no base or no block |
| `tests-with-code` and `commands` don't read tier | same file | neither references `ctx.tier` |
