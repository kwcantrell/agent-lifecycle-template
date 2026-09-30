## 1. Tests first

- [x] 1.1 Write failing tests in a new `ChangedPathsTest` class in `tests/test_check_change.py`:
  - `test_path_with_space_read_whole`;
  - `test_rename_lists_both_sides` (moving `scripts/x.sh` out makes `risk-floor` name `scripts/x.sh`).
  Evidence: `python3 -m unittest tests.test_check_change.ChangedPathsTest tests.test_check_change.ArchiveTaskEditTest` on unfixed code -> `FAILED (failures=9)`, including `test_path_with_space_read_whole` and `test_rename_lists_both_sides`
- [x] 1.2 Write failing tests in a new `ArchiveTaskEditTest` class:
  - `test_tasks_only_edits_to_two_archives_pass` (PASS tier 0, both named);
  - `test_archive_edit_alongside_own_change`;
  - `test_exempt_and_counted_archive` (only B counted, A named);
  - `test_note_survives_failure` (two change dirs plus an exempt archive: FAIL, archive named);
  - `test_grandfathered_archive_tasks_only_is_exempt`.
  Evidence: same run -> FAIL for all five: `test_tasks_only_edits_to_two_archives_pass`, `test_archive_edit_alongside_own_change`, `test_exempt_and_counted_archive`, `test_note_survives_failure`, `test_grandfathered_archive_tasks_only_is_exempt`
- [x] 1.3 Write regression tests, run against the unfixed code (record which pass already):
  - `test_archive_other_file_counts`;
  - `test_file_moved_out_of_archive_counts`;
  - `test_tasks_added_deleted_moved_or_symlinked_counts`;
  - `test_hidden_name_beside_tasks_counts` (`tasks.md x.txt`);
  - `test_non_archive_name_never_exempt`;
  - `test_new_archive_counts`;
  - `test_moved_in_flight_change_plus_exempt_edit`;
  - `test_pr_tier1_with_only_exempt_edits_fails`;
  - `test_no_base_no_exemption`.
  Evidence: same run -> 7 of 9 pass on unfixed code (every archive edit is counted today); `test_pr_tier1_with_only_exempt_edits_fails` and `test_moved_in_flight_change_plus_exempt_edit` fail (they need the exemption)

## 2. Fix

- [x] 2.1 `changed_files`: `-z` on every git call, and `--no-renames` on both `git diff` calls (design
  decision 1). The test for this is 1.1, which now passes.
  Evidence: `python3 -m unittest tests.test_check_change.ChangedPathsTest` -> `OK`; mutation back to `--name-only base ... .split()` -> `FAILED (failures=2)` after the tests were widened to committed and uncommitted cases
- [x] 2.2 Add `exempt_archives(base)` (decision 2), and wrap `check_change` to drop exempt dirs and
  append the note (decision 3). The tests for this are 1.2 and 1.3, which all now pass.
  Evidence: `... ArchiveTaskEditTest` -> `Ran 16 tests ... OK`; mutations: accept a symlink -> `failures=8`, any name -> `failures=3`, ignore untracked -> `failures=1`, note on PASS only -> `failures=1, errors=1`; dropping `on_base` survives (redundant: an `M` record for tasks.md implies the dir is on base)
- [x] 2.3 Write docs. These are docs only, so no test.
  - `docs/decisions/0016-archived-task-edits.md`;
  - the residual line and grandfathering wording in `docs/security.md`;
  - the `change` row in `docs/lifecycle.md`.
  Evidence: `git diff --stat` -> `docs/lifecycle.md | 2 +-`, `docs/security.md | 6 ++`, new `docs/decisions/0016-archived-task-edits.md`
- [x] 2.4 Run `python3 -m unittest discover -s tests` and `scripts/check-change.sh --stage hook`,
  and record both as `Evidence:`.
  Evidence: `python3 -m unittest discover -s tests` -> `Ran 100 tests ... OK`; `scripts/check-change.sh --stage hook` -> all PASS, rc=0

## 3. Archive

- [ ] 3.1 Archive with the delta synced into `openspec/specs/gate-checker/spec.md`, and run
  `openspec validate --all --strict`.
