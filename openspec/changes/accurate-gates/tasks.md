## 1. Tests first

- [ ] 1.1 Write failing panel tests in `tests/test_check_change.py`: `test_prose_panel_fails`, `test_no_findings_panel_passes`, `test_no_findings_in_code_block_fails`, `test_untagged_panel_item_fails` (no tag and `[Critical]`), `test_nested_sub_bullet_not_a_finding`, `test_ticked_critical_needs_resolution`
- [ ] 1.2 Write failing tests `test_nested_tests_dir_counts_as_tests`, `test_managed_paths_ignored_by_tests_with_code`, `test_managed_paths_ignored_by_size`, `test_pr_cannot_grant_own_exemption`
- [ ] 1.3 Write failing tests in `tests/test_init.py`: `test_init_sets_managed_paths` (exact list; this repo keeps `[]`) and `test_init_keeps_existing_managed_paths`

## 2. Fix

- [ ] 2.1 `check_panel` per design 1; 1.1 passes
- [ ] 2.2 Base-branch exemption config (design 4), `managed_paths` in tests-with-code and size, depth-agnostic default `test_globs` and `managed_paths: []` in config.yaml with comments; 1.2 passes
- [ ] 2.3 `init.sh` sets the exact `managed_paths` list; 1.3 passes
- [ ] 2.4 Update the docs/lifecycle.md check table, the docs/security.md known gaps, and the adversarial-panel skill (`No findings.`, tag rules); run `scripts/sync-skills.sh`
- [ ] 2.5 Run the full suite and `scripts/check-change.sh --stage hook`; record them as `Evidence:`

## 3. Archive

- [ ] 3.1 After archive, confirm `openspec validate --all --strict` passes with the merged `gate-checker` spec
