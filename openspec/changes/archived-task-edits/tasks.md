## 1. Tests first

- [ ] 1.1 Write failing tests in a new `ChangedPathsTest` class in `tests/test_check_change.py`:
  - `test_path_with_space_read_whole`;
  - `test_rename_lists_both_sides` (moving `scripts/x.sh` out makes `risk-floor` name `scripts/x.sh`).
- [ ] 1.2 Write failing tests in a new `ArchiveTaskEditTest` class:
  - `test_tasks_only_edits_to_two_archives_pass` (PASS tier 0, both named);
  - `test_archive_edit_alongside_own_change`;
  - `test_exempt_and_counted_archive` (only B counted, A named);
  - `test_note_survives_failure` (two change dirs plus an exempt archive: FAIL, archive named);
  - `test_grandfathered_archive_tasks_only_is_exempt`.
- [ ] 1.3 Write regression tests, run against the unfixed code (record which pass already):
  - `test_archive_other_file_counts`;
  - `test_file_moved_out_of_archive_counts`;
  - `test_tasks_added_deleted_moved_or_symlinked_counts`;
  - `test_hidden_name_beside_tasks_counts` (`tasks.md x.txt`);
  - `test_non_archive_name_never_exempt`;
  - `test_new_archive_counts`;
  - `test_moved_in_flight_change_plus_exempt_edit`;
  - `test_pr_tier1_with_only_exempt_edits_fails`;
  - `test_no_base_no_exemption`.

## 2. Fix

- [ ] 2.1 `changed_files`: `-z` on every git call, and `--no-renames` on both `git diff` calls (design
  decision 1). The test for this is 1.1, which now passes.
- [ ] 2.2 Add `exempt_archives(base)` (decision 2), and wrap `check_change` to drop exempt dirs and
  append the note (decision 3). The tests for this are 1.2 and 1.3, which all now pass.
- [ ] 2.3 Write docs. These are docs only, so no test.
  - `docs/decisions/0016-archived-task-edits.md`;
  - the residual line and grandfathering wording in `docs/security.md`;
  - the `change` row in `docs/lifecycle.md`.
- [ ] 2.4 Run `python3 -m unittest discover -s tests` and `scripts/check-change.sh --stage hook`,
  and record both as `Evidence:`.

## 3. Archive

- [ ] 3.1 Archive with the delta synced into `openspec/specs/gate-checker/spec.md`, and run
  `openspec validate --all --strict`.
