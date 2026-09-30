## 1. Tests first

- [ ] 1.1 Write failing tests in `tests/test_check_change.py` (`YamlParseTest`): `test_broken_yaml_fails_with_line`, `test_tags_and_multidoc_pass`, `test_constructor_and_nesting_errors_fail_per_file`, `test_preexisting_broken_warns_in_hook_fails_in_pr`, `test_symlinks_skipped`, `test_precommit_shape_checked`, `test_untracked_checked_locally_not_in_ci`

## 2. Fix

- [ ] 2.1 `check_yaml` per design 1-5 and 7; add it to the `commit`, `hook` and `pr` stages; 1.1 passes
- [ ] 2.2 Add ADR 0016 (including the templated-YAML limitation) and the docs/lifecycle.md check table row
- [ ] 2.3 Run the full suite and `scripts/check-change.sh --stage hook`; record them as `Evidence:`

## 3. Archive

- [ ] 3.1 After archive, confirm `openspec validate --all --strict` passes
