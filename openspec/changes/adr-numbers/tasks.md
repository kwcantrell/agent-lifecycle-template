## 1. Tests first

- [x] 1.1 Write failing tests in `tests/test_check_change.py` (`AdrNumberTest`): `test_duplicate_added_fails_every_stage`, `test_preexisting_duplicate_warns_in_hook_fails_in_pr`, `test_renames_pass`, `test_other_naming_ignored`
  Evidence: before the check existed -> `FAILED (failures=7)` across all 4 tests

## 2. Fix

- [x] 2.1 `check_adr` per design 1-3; add it to the `commit`, `hook` and `pr` stages; 1.1 passes
  Evidence: `python3 -m unittest discover -s tests` -> `Ran 129 tests ... OK`; `--only adr` on main -> `PASS 18 ADR number(s) unique`; on a worktree at `a9b9130` (post-#9) -> `FAIL adr duplicate ADR numbers ... 0016: 0016-archived-task-edits.md, 0016-config-files-must-parse.md`
- [x] 2.2 Add ADR 0018 (with the renumbering gap), the docs/lifecycle.md row, and the docs/security.md setup item with the bypass caveat
  Evidence: `docs/decisions/0018-adr-numbers-unique.md`; docs/lifecycle.md `| adr |` row; docs/security.md setup item 7 with the bypass caveat
- [x] 2.3 Run the full suite and `scripts/check-change.sh --stage hook`; record them as `Evidence:`
  Evidence: full suite OK (129); `scripts/check-change.sh --stage hook --quiet` -> rc=0

## 3. Archive

- [ ] 3.1 After archive, confirm `openspec validate --all --strict` passes
