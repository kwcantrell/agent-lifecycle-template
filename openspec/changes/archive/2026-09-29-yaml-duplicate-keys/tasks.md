## 1. Tests first

- [x] 1.1 Write failing tests in `tests/test_check_change.py` (`YamlParseTest`): `test_introduced_duplicate_fails_with_key_and_line`, `test_duplicate_equality_and_tags`, `test_merge_keys_exempt`, `test_inherited_duplicate_only_warns`
  Evidence: before the fix -> `FAILED (failures=5)`; `test_merge_keys_exempt` passed as a regression guard

## 2. Fix

- [x] 2.1 `TolerantLoader.construct_mapping` and introduced-vs-inherited per design 1-5; 1.1 passes, and the existing yaml tests still pass
  Evidence: `python3 -m unittest discover -s tests` -> `Ran 133 tests ... OK`; `--only yaml` on this repo -> `PASS 16 YAML file(s) parse`
- [x] 2.2 Update the docs/lifecycle.md yaml row, and add the ADR 0017 amendment (design 6)
  Evidence: docs/lifecycle.md yaml row mentions introduced duplicate keys; ADR 0017 `Amended 2026-09-29 (yaml-duplicate-keys)` in Decision; Consequences sentence replaced
- [x] 2.3 Run the full suite and `scripts/check-change.sh --stage hook`; record them as `Evidence:`
  Evidence: full suite OK (133); `scripts/check-change.sh --stage hook --quiet` -> rc=0

## 3. Archive

- [x] 3.1 After archive, confirm `openspec validate --all --strict` passes
  Evidence: `openspec validate --all --strict` -> `Totals: 3 passed, 0 failed`
