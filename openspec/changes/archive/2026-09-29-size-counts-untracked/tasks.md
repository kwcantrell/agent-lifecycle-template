## 1. Tests first

- [x] 1.1 Write failing tests in `tests/test_check_change.py` (`UntrackedSizeTest`): `test_size_counts_untracked_files`, `test_size_skips_excluded_ignored_binary_untracked`, `test_size_untracked_odd_names`, `test_size_counts_last_line_without_newline`, `test_size_ci_ignores_untracked`, `test_hook_stage_warns_on_size`
  Evidence: before the fix -> `FAILED (failures=5)`; `test_size_ci_ignores_untracked` passed as a regression guard (CI behaviour unchanged)

## 2. Fix

- [x] 2.1 `check_size` per design 1-3 (`ctx.stage`; `-z` listing; regular files; symlink = 1; git line and binary rules; streamed with a cap); `size` in the hook stage; 1.1 passes
  Evidence: `python3 -m unittest discover -s tests` -> `Ran 90 tests ... OK`
- [x] 2.2 Amend ADR 0007; update the docs/lifecycle.md size row (hook column: WARN) and the scratch-file note
  Evidence: ADR 0007 `Amended 2026-09-29` paragraph + loophole note; docs/lifecycle.md size row `| size | | warn | x |` and scratch-file note; `.pre-commit-config.yaml` lifecycle-push `verbose: true`, so the pre-push warning is visible (the panel missed that pre-commit hides passing output)
- [x] 2.3 Run the full suite and `scripts/check-change.sh --stage hook`; record them as `Evidence:`
  Evidence: full suite OK (90); `scripts/check-change.sh --stage hook --quiet` -> rc=0

## 3. Archive

- [x] 3.1 After archive, confirm `openspec validate --all --strict` passes
  Evidence: `openspec validate --all --strict` -> `Totals: 3 passed, 0 failed`
