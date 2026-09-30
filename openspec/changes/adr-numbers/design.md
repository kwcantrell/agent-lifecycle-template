# Design: ADR numbers are unique

Revised after the panel (see panel.md).

## Decisions

1. **Files.** `git ls-files -z -- docs/decisions`, plus, when not in CI,
   `git ls-files -z --others --exclude-standard -- docs/decisions`. Files at the top level of that
   directory match `^(\d{4})-.+\.md$`, with the extension case-insensitive (`.MD`). The number is
   the group. `0000-adr-template.md` counts like any other: a second `0000-*` is a duplicate.
   [F-m2]
2. **Duplicates in the resulting tree.** Files are grouped by number. Any group of more than one is
   a duplicate, named with all its files. Renames need no special case: only the resulting names
   count, so a slug-only rename or a renumbered new ADR is fine. [A-M1, A-m1]
3. **Stage-aware severity.** At the `pr` stage (and `--only`), any duplicate means FAIL. At the
   `commit` and `hook` stages, a duplicate group containing a file in `ctx.changed` means FAIL;
   otherwise it's a WARN, "pre-existing duplicate ADR numbers: fix in their own change". The WARN
   prints under `--quiet`. [F-M2]
4. **No latest-base comparison.** PR CI runs on GitHub's merge commit, which catches the #8/#9 case
   (#8 was merged before #9's CI ran). Comparing locally against `origin/main` would falsely fail on
   slug-only renames and silently miss on stale refs. [S-M1, F-M3, A-M1]
5. **Ruleset setting.** It's documented only, in docs/security.md "Setup a human must do", with the
   caveat that the admin bypass ignores it, so the duplicate check on the merge commit is the real
   control. It's not part of this change's scope. [S-M2, F-m1]
6. **Renumbering merged ADRs** isn't forbidden. #10 renumbered a merged ADR, with human review and a
   note. The gap is stated in ADR 0018. [F-M1, declined pending approver]

## Assumptions

| Assumption | Command | Observed |
| --- | --- | --- |
| #8 merged before #9's CI ran | git log times | #8 merge 19:57:10; #9's 0016 commit 19:59:06; #9 merge 20:01:33 |
| The ruleset doesn't require up-to-date branches, and admins bypass | `gh api .../rulesets/24211447` | `strict...: false`; `bypass_actors` admin `pull_request` |
| The current tree has no duplicates | `ls docs/decisions \| grep -o '^[0-9]\{4\}' \| sort \| uniq -d` | empty |
| A move shows both paths in `ctx.changed` (`--no-renames`) | panel repro | `0016-a.md 0016-b.md` |
