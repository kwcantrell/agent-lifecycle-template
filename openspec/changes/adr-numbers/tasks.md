## 1. Tests first

- [ ] 1.1 Write failing tests in `tests/test_check_change.py` (`AdrNumberTest`): `test_duplicate_added_fails_every_stage`, `test_preexisting_duplicate_warns_in_hook_fails_in_pr`, `test_renames_pass`, `test_other_naming_ignored`

## 2. Fix

- [ ] 2.1 `check_adr` per design 1-3; add it to the `commit`, `hook` and `pr` stages; 1.1 passes
- [ ] 2.2 Add ADR 0018 (with the renumbering gap), the docs/lifecycle.md row, and the docs/security.md setup item with the bypass caveat
- [ ] 2.3 Run the full suite and `scripts/check-change.sh --stage hook`; record them as `Evidence:`

## 3. Archive

- [ ] 3.1 After archive, confirm `openspec validate --all --strict` passes
