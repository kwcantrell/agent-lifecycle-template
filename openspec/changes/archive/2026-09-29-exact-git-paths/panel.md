# Panel: exact-git-paths

Tier: 2 · Reviewers: assumption tester (A), failure and abuse (F), scope and simplicity (S), each a separate Sonnet subagent · Date: 2026-09-29

No critical or major findings. One decision went to the owner (moves), who chose rename-aware counting. That redesign gets a delta re-panel below.

- [x] [minor] A-5 / F-MOVE-DOUBLE / S-1 (A, F, S): with `--no-renames`, every move costs twice its lines: an 8-line move fails a 10-line budget (`PASS size 0/10` before, `FAIL 16` after). Routine refactors would lean on `size-override`, and no scenario or test pinned the behaviour. Resolved: the owner chose rename-aware counting (proposal "Decisions"; design 2), with scenarios and tests for all four move directions and for a pure move.
- [x] [minor] A-2 (A): an empty numstat output is `''`, and `''.split("\t", 2)` would raise ValueError without filtering. Resolved: design 2 skips empty fields; spec scenario "Nothing changed"; test `test_empty_diff_counts_zero`.
- [x] [minor] A-1 (A): the stray-file test could not pass "before and after" while asserting the file's name (before, `['src/a', 'b.py']`). Resolved: it moved to 1.1 as a failing-first test `test_stray_file_with_space_is_named`.
- [x] [minor] A-3 / S-7 (A, S): task 2.3's grep check would also match the renamed ADR's own note. Resolved: the check is now `git grep -ln "0016-config-files" -- . ':!openspec/changes/archive'`, whose expected output is the note's file only.
- [x] [minor] A-4 / F-ADR-DANGLE (A, F): yaml-parse-gate's archived records name the old ADR path; installed repos may hold a copy numbered 0016, and a re-install adds 0017 beside it. Accepted as residuals by the author, for the approver to confirm (design "Accepted residuals"). The ADR note maps old to new, and nothing validates archived paths.
- [x] [minor] S-2 (S): ADR 0016's `Rule:` line should record that the rule now covers these gates. Resolved: design 4, task 2.3.
- [x] [minor] S-3 (S): `docs/lifecycle.md`'s size row doesn't say how moves count. Resolved: design 4, task 2.3.
- [x] [minor] S-4 (S): the ADR renumber is unrelated to path parsing, and a separate tier 0 PR would be cleaner. Declined by human: the owner asked for one PR.
- [x] [minor] F-RESIDUAL-EVASION (F): existing size blind spots (binary files 0, symlinks and gitlinks 1, merge commits skipped by artifacts-first) are unchanged. Resolved: stated as non-goals and residuals.
- [x] [minor] F-AF-ARCHIVE-PREFIX (F): artifacts-first accepts any `openspec/changes/` path; nothing pins that a stray file mixed with an archive path is still caught. Resolved: `test_stray_file_with_space_is_named` includes an archive path.
- [x] [minor] S-5 / S-6 (S): informational. `--no-renames` was consistent with ADR 0016; the MODIFIED requirement preserves the prior scenarios; the size is well under budget.

## Re-panel 2026-09-29
Delta: rename-aware size counting (owner decision after the first panel). Reviewers: assumption tester (RA) and failure and abuse (RF), each a separate Sonnet subagent.

- [x] [major] RF-NEG-COST (RF): the drafted counted-to-excluded cost `untracked_lines(new) - a + d` goes negative when `untracked_lines` disagrees with git. `.gitattributes` `*.dat diff` makes git count a NUL-bearing file as text, while `untracked_lines` says 0. Moving it into `tests/` with +100 lines gave -100: a budget credit. Evidence: prototype, numstat `100 0 |src/n.dat|tests/n.dat`, `untracked_lines` -> 0. Resolved: design 2 now takes every count from git (`--numstat -z --no-renames`) and uses `-M` only to replace counted-to-counted moves with their own delta. It never reads the working tree, so no cost can go negative. Spec scenario "A file git counts as text, moved into an exclusion", test `test_text_attr_move_into_excluded_never_negative`.
- [x] [major] RA-1 (RA): `test_rename_detection_ignores_config` was filed as already passing, but it fails today: `diff.renames=false` without `-M` counts the 8-line move as 16. Resolved: moved to 1.1 (failing first).
- [x] [minor] RA-4 (RA): `untracked_lines` with a small or negative cap returns a partial count, which was wrong inside the drafted formula. Resolved: that formula is gone (design 2 reads no files).
- [x] [minor] RF-BIN-RENAME-PARSE (RF): a binary rename record `-\t-\t\0old\0new` must still consume its two path fields. Resolved: design 2 walks the fields with an index. Spec scenario "Binary move followed by other changes", test `test_binary_move_then_edit_counts_edit`.
- [x] [minor] RA-5 (RA): a small file with edits can fall below git's 50% similarity. Resolved: the scenario and test use a 20-line file.
- [x] [minor] RA-2 / RF-RENAME-LIMIT-FALLBACK (RA, RF): past `diff.renameLimit`, `-M` degrades to delete plus add. That fails closed and may differ between machines. Resolved: the spec claim is narrowed to `diff.renames`, and the design records it as a residual; `-l0` is not used because of its O(n²) cost.
- [x] [minor] RF-SIMILARITY-DISCOUNT (RF): a delete plus add that is at least 50% similar costs its delta (360 against 800 in the example), the same as an in-place edit. Accepted as a residual by the author, for the approver to confirm (design "Accepted residuals"). It follows from the owner's choice of rename-aware counting.
- [x] [minor] RA-3 / RF-LOCAL-CI-ASYMMETRY (RA, RF): an unstaged `mv` counts twice locally until `git add`, while CI sees committed renames. Resolved: recorded as a residual. The hook stage only warns, and tests commit their moves.
- [x] [minor] RF-TWO-PR-LAUNDER-UNTESTED (RF): moving from `tests/` back to `src/` in a later PR costs the whole file, which closes the two-PR laundering path. Resolved: pinned by `test_move_from_excluded_into_source_counts_whole_file`. Within one PR, a round trip nets to a counted-to-counted move.

## Consistency read 2026-09-29
Reader: a separate Sonnet subagent, read-only, before archive. Documents read: proposal.md, design.md, specs/gate-checker/spec.md, tasks.md, panel.md, `committed_lines`, `check_artifacts_first`, `check_size`, `GatePathsTest`, ADRs 0016 and 0017, docs/lifecycle.md.
Edits since approval: tasks.md (1.1-2.4 ticked with `Evidence:` lines). Scope change: no.
- [x] [minor] Task 2.3's check still expected the note's file, which its own evidence showed to be wrong. Resolved: reworded to expect no live file after archive; verified after archive (task 3.1).
- [x] [minor] A-3 above and design.md's assumptions table repeat the wrong expectation. Accepted: panel-log and design history only; no normative text depends on it.
