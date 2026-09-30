## 1. Tests first

- [ ] 1.1 Write failing tests in a new `GatePathsTest` class in `tests/test_check_change.py`:
  - `test_plan_commit_with_space_and_non_ascii_passes`;
  - `test_stray_file_with_space_is_named` (`src/a b.py` beside an archive path: FAIL naming `src/a b.py`);
  - `test_non_ascii_path_matches_size_exclusion`;
  - `test_move_from_excluded_into_source_counts_whole_file` (51, FAIL);
  - `test_move_from_source_into_excluded_counts_old_file` (50, FAIL);
  - `test_move_with_edits_counts_delta` (20-line file, 3);
  - `test_rename_detection_ignores_config` (`diff.renames false`, pure move: PASS; fails today with 16);
  - `test_text_attr_move_into_excluded_never_negative` (33).
- [ ] 1.2 Write regression tests, recording which already pass:
  - `test_pure_move_in_source_costs_nothing` (0, PASS);
  - `test_binary_move_then_edit_counts_edit` (3);
  - `test_empty_diff_counts_zero`.

## 2. Fix

- [ ] 2.1 `check_artifacts_first`: `diff-tree ... -z`, split on NUL (design 1). The artifacts-first
  tests in 1.1 now pass.
- [ ] 2.2 `check_size`: count from `--numstat -z --no-renames`, and replace counted-to-counted
  renames found by `--numstat -z -M` with their own delta (design 2). The size tests in 1.1 and 1.2
  now pass. Tests stage or commit their moves (`Repo.commit`).
- [ ] 2.3 Rename the YAML ADR to 0017, with its heading and note (design 3). Extend ADR 0016's
  `Rule:` line and `docs/lifecycle.md`'s size row (design 4). These are docs, so no test. Check:
  `git grep -ln "0016-config-files" -- . ':!openspec/changes/archive'` prints only
  `docs/decisions/0017-config-files-must-parse.md`, the note.
- [ ] 2.4 Run `python3 -m unittest discover -s tests` and `scripts/check-change.sh --stage hook`,
  and record both as `Evidence:`.

## 3. Archive

- [ ] 3.1 Archive with the delta synced into `openspec/specs/gate-checker/spec.md`, and run
  `openspec validate --all --strict`.
