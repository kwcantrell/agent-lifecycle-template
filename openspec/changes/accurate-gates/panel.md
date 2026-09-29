# Panel: accurate-gates

Tier: 2 · Reviewers: assumption tester (A), failure and abuse (F), scope and simplicity (S), each a separate Sonnet subagent · Date: 2026-09-29

Findings were de-duplicated across reviewers, and each id shows who raised it. All are resolved
in the revised proposal, design, spec and tasks, or recorded as stated known gaps. None were
declined.

- [x] [critical] A-C1: the init merge's `setdefault` would copy the template's `managed_paths: []` into a new target, so the installer would fill nothing. Evidence: simulated merge -> `{'managed_paths': []}`. Resolved: design 3 sets `defaults["managed_paths"]` explicitly; test `test_init_sets_managed_paths`.
- [x] [major] F-M3: `managed_paths` (and `test_globs`) are read from the working tree, so the same PR can exempt its own files. In a target without a human CODEOWNER on config.yaml, nothing stops it. Evidence: check_change.py:242 reads config from the working tree. Resolved: design 4 reads exemptions from the base branch, with test `test_pr_cannot_grant_own_exemption`. The cross-PR and vendored-checker residue is a stated known gap.
- [x] [major] F-M2: the panel gate checks format, not honesty (a mis-tagged critical, or `No findings.` over prose). The `[critical]` search matched anywhere in a block. Evidence: check_change.py:194-198. Resolved: design 1 anchors the tag as the first token and requires `Resolved:`/`Declined` on ticked critical and major findings. Honesty is a stated known gap, and the human approver is the control.
- [x] [major] F-M4: the stricter gate could break tier 1 prose panels, consistency-read and re-panel sections, and nested sub-bullets. Evidence: check_change.py:127 matches indented items. Resolved: design 1 treats only column-0 items as findings, and applies to every tier because the skill's format covers all tiers. Consistency-read and re-panel append tagged items. Tests `test_nested_sub_bullet_not_a_finding` and `test_prose_panel_fails`.
- [x] [major] F-M1: wider `test_globs` also widen the size exclusion, so source under `tests/` escapes both gates. Evidence: check_change.py:246, :260. Resolved: stated as a known gap in docs/security.md. Counting test files toward size is out of scope (it changes ADR 0007).
- [x] [major] A-M2: existing installs keep their old `test_globs` and get no `managed_paths`, so the infisical false FAIL isn't fixed there. Evidence: infisical-copy config has root-only globs. Resolved: stated as a non-goal and moved to change A (safe adoption, re-running init.sh).
- [x] [major] A-M3: the contents of `managed_paths` were unspecified. A directory entry such as `.claude/hooks` doesn't match its files, and a broad glob would swallow the target's own scripts. Evidence: `matches('scripts/lib/other.py', exact list)` -> False. Resolved: design 3 lists the 5 exact files.
- [x] [major] A-M4 / F-m2: `No findings.` was spoofable (inside a fence or a comment) and brittle (trailing space), and it wasn't said whether it can sit alongside items. Evidence: line-equality probe -> True in a fence and in a comment, False with a trailing space. Resolved: design 1 strips lines, drops code and comments, and consults the line only when there are zero findings. Test `test_no_findings_in_code_block_fails`.
- [x] [major] S-M1: the docs/lifecycle.md check table would be wrong for panel, tests-with-code and size. Evidence: docs/lifecycle.md:56, :59-60. Resolved: task 2.4.
- [x] [major] S-M2: "a target keeps its managed_paths" had no scenario or test. Resolved: spec scenario "Installer keeps a target's value"; test `test_init_keeps_existing_managed_paths`.
- [x] [minor] A-m1: tag parsing was looser than the design (`[Critical]`, numbered lists, nested items). Resolved: design 1 uses exact lowercase tags and column-0 dash items only; test `test_untagged_panel_item_fails` covers `[Critical]`.
- [x] [minor] A-m2 / F-m1: glob false positives. `**/tests/**` doesn't match `contest/` or `latest/`, but `**/test_*` can match `test_helper.sh`. Resolved: the `**/test_*` behaviour predates this change and is noted in the known gaps.
- [x] [minor] S-m1: one test bundled two gates. Resolved: split into `test_managed_paths_ignored_by_tests_with_code` and `test_managed_paths_ignored_by_size`.
- [x] [minor] S-m2: mixed panels (`No findings.` alongside items, an untagged `[x]`) were undefined. Resolved: design 1 covers both.
- [x] [minor] S-m3: say why `size_exclude` isn't reused, and add config comments. Resolved: design 3 and task 2.2.
- [x] [minor] S-m4: no ADR or README update needed; size is within budget. Resolved: none needed, confirmed.
