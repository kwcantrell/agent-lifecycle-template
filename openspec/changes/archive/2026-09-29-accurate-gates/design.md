# Design: accurate gates

Revised after the panel (see panel.md). Finding ids are given in brackets.

## Decisions

1. **Panel format is enforced.** [original problem; A-M4, A-m1, F-M2, F-M4, F-m2, S-m2]
   - Parsing: fenced code blocks and HTML comments are dropped first. A finding is a line at
     column 0 matching `- [ ]`, `- [x]` or `- [X]`. Indented checklist lines are sub-bullets of
     the item above, not findings.
   - The first token after the checkbox must be exactly `[critical]`, `[major]` or `[minor]`,
     lowercase as the skill documents. Anything else, such as `[Critical]` or no tag, is an
     untagged item and fails, naming up to 3.
   - Zero findings fails, unless a line whose stripped text is exactly `No findings.` exists
     outside code and comments. That line is only consulted when there are zero findings.
   - An open `[critical]` fails, as today. A ticked `[critical]` or `[major]` must contain
     `Resolved:` or `Declined` (the skill's rule: tick only with how it was resolved).
   - This applies to every tier that has a panel.md, tier 1 included, since the skill's format
     covers every tier. Consistency-read and re-panel sections append tagged items to the same file.
2. **Test folders at any depth.** The defaults become `**/test/**`, `**/tests/**`, `**/__tests__/**`
   plus the existing file patterns. `**/` matches zero directories, so a root `tests/` still
   matches, and `contest/` or `latest/` don't. [A-m2]
3. **`managed_paths`, exact files only, filled by init.sh.** [A-C1, A-M3, S-M2]
   - init.sh sets `defaults["managed_paths"]` explicitly, as it does for `commands`, to the
     exact installed files: `scripts/check-change.sh`, `scripts/sync-skills.sh`,
     `scripts/lib/check_change.py`, `.claude/hooks/guard-approval.sh`,
     `.claude/hooks/stop-check.sh`. Exact paths never swallow a target's own `scripts/` files.
   - `setdefault` keeps a target's existing value.
   - Both `check_tests_with_code` (dropping them from source) and `check_size` (adding them to
     exclude) read it.
   - Why not reuse `size_exclude`: only size reads it, and tests-with-code needs the exemption
     too. [S-m3]
4. **Exemptions come from the base branch.** `managed_paths`, `test_globs`, `size_exclude` and
   `size_budget` are read from `git show <base>:openspec/config.yaml` when the base has that file,
   and from the working tree otherwise (for example, the install commit). A PR can change them,
   but its own gates use the old values. [F-M3]
5. **Docs.** docs/lifecycle.md check-table rows for panel, tests-with-code and size; config.yaml
   comments for `managed_paths` and test globs; the adversarial-panel skill documents
   `No findings.` and the tag rules. [S-M1, S-m3]

## Known gaps (stated in docs/security.md)

- The panel gate checks structure, not honesty. A `[minor]` tag on a real critical, or
  `No findings.` over prose criticals, passes. The human approver is the control. [F-M2]
- Files under test folders are excluded from the size budget and count as tests, so source
  hidden in `tests/` evades both gates. Code review is the control. [F-M1, F-m1]
- Where a target has no human CODEOWNER on `openspec/config.yaml`, a later PR can widen
  exemptions (decision 4 only stops same-PR widening). A modified vendored checker isn't
  detected either. [F-M3]

## Alternatives considered

- Hard-coding managed paths in check_change.py: rejected, because this repo couldn't then count
  its own source.
- Counting test-folder files toward size: rejected for now. It changes ADR 0007's budget
  semantics, so it would need its own change.

## Assumptions

| Assumption | Command | Observed |
| --- | --- | --- |
| infisical's panel.md has no checklist items but discusses criticals | `grep -c "^- \[" panel.md; grep -ci critical panel.md` (infisical copy) | `0`, `7` |
| Nested tests are missed today | template gates on the infisical in-flight branch | `FAIL tests-with-code ... ['docker-compose.yml', 'scripts/backup.sh', ...]` |
| `**/tests/**` matches root and deep paths, not `contest/` | `matches()` probes (assumption tester) | `tests/x True`, `scripts/tests/t.sh True`, `contest/x False`, `latest/x False` |
| The install trips tests-with-code | template gates on the installed infisical copy | `FAIL tests-with-code ... ['scripts/check-change.sh', ...]` |
| A plain merge would copy `managed_paths: []` | simulated init merge (assumption tester) | `{'managed_paths': []}` for a new target; an existing `['x']` is kept |
| This repo's archived panels already meet the new format | `grep -c` of tagged items; every ticked critical/major says `Resolved:` | 12 and 14 tagged items, none untagged |
