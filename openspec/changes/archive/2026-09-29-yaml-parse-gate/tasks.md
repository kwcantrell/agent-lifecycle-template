## 1. Tests first

- [x] 1.1 Write failing tests in `tests/test_check_change.py` (`YamlParseTest`): `test_broken_yaml_fails_with_line`, `test_tags_and_multidoc_pass`, `test_constructor_and_nesting_errors_fail_per_file`, `test_preexisting_broken_warns_in_hook_fails_in_pr`, `test_symlinks_skipped`, `test_precommit_shape_checked`, `test_untracked_checked_locally_not_in_ci`
  Evidence: before the check existed -> `FAILED (failures=10)` across all 7 tests

## 2. Fix

- [x] 2.1 `check_yaml` per design 1-5 and 7; add it to the `commit`, `hook` and `pr` stages; 1.1 passes
  Evidence: `python3 -m unittest discover -s tests` -> `Ran 97 tests ... OK`; the initial commit's `.pre-commit-config.yaml` -> `.pre-commit-config.yaml:26: mapping values are not allowed here`; today's file -> parses; `--only yaml` -> `PASS 12 YAML file(s) parse`
- [x] 2.2 Add ADR 0016 (including the templated-YAML limitation) and the docs/lifecycle.md check table row
  Evidence: `docs/decisions/0016-config-files-must-parse.md`; docs/lifecycle.md `| yaml | x | x | x |` row
- [x] 2.3 Run the full suite and `scripts/check-change.sh --stage hook`; record them as `Evidence:`
  Evidence: full suite OK (97); `scripts/check-change.sh --stage hook --quiet` -> rc=0

## 3. Archive

- [x] 3.1 After archive, confirm `openspec validate --all --strict` passes
  Evidence: `openspec validate --all --strict` -> `Totals: 3 passed, 0 failed`
