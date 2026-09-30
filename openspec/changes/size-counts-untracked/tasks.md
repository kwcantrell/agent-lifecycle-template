## 1. Tests first

- [ ] 1.1 Write failing tests in `tests/test_check_change.py` (`UntrackedSizeTest`): `test_size_counts_untracked_files`, `test_size_skips_excluded_ignored_binary_untracked`, `test_size_untracked_odd_names`, `test_size_counts_last_line_without_newline`, `test_size_ci_ignores_untracked`, `test_hook_stage_warns_on_size`

## 2. Fix

- [ ] 2.1 `check_size` per design 1-3 (`ctx.stage`; `-z` listing; regular files; symlink = 1; git line and binary rules; streamed with a cap); `size` in the hook stage; 1.1 passes
- [ ] 2.2 Amend ADR 0007; update the docs/lifecycle.md size row (hook column: WARN) and the scratch-file note
- [ ] 2.3 Run the full suite and `scripts/check-change.sh --stage hook`; record them as `Evidence:`

## 3. Archive

- [ ] 3.1 After archive, confirm `openspec validate --all --strict` passes
