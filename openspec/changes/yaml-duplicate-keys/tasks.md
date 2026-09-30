## 1. Tests first

- [ ] 1.1 Write failing tests in `tests/test_check_change.py` (`YamlParseTest`): `test_introduced_duplicate_fails_with_key_and_line`, `test_duplicate_equality_and_tags`, `test_merge_keys_exempt`, `test_inherited_duplicate_only_warns`

## 2. Fix

- [ ] 2.1 `TolerantLoader.construct_mapping` and introduced-vs-inherited per design 1-5; 1.1 passes, and the existing yaml tests still pass
- [ ] 2.2 Update the docs/lifecycle.md yaml row, and add the ADR 0017 amendment (design 6)
- [ ] 2.3 Run the full suite and `scripts/check-change.sh --stage hook`; record them as `Evidence:`

## 3. Archive

- [ ] 3.1 After archive, confirm `openspec validate --all --strict` passes
