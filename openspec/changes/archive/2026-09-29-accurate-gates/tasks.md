## 1. Tests first

- [x] 1.1 Write failing panel tests in `tests/test_check_change.py`: `test_prose_panel_fails`, `test_no_findings_panel_passes`, `test_no_findings_in_code_block_fails`, `test_untagged_panel_item_fails` (no tag and `[Critical]`), `test_nested_sub_bullet_not_a_finding`, `test_ticked_critical_needs_resolution`
  Evidence: before the fix -> `FAIL` for prose, code-block, untagged (x3) and ticked-critical; `test_no_findings_panel_passes`, `test_nested_sub_bullet_not_a_finding` and `test_open_critical_still_fails` passed as regression guards
- [x] 1.2 Write failing tests `test_nested_tests_dir_counts_as_tests`, `test_managed_paths_ignored_by_tests_with_code`, `test_managed_paths_ignored_by_size`, `test_pr_cannot_grant_own_exemption`
  Evidence: with `scripts/lib/check_change.py` stashed -> `FAIL: test_managed_paths_ignored_by_size`, `FAIL: test_managed_paths_ignored_by_tests_with_code`; `test_nested_tests_dir_counts_as_tests` failed before the config change
- [x] 1.3 Write failing tests in `tests/test_init.py`: `test_init_sets_managed_paths` (exact list; this repo keeps `[]`) and `test_init_keeps_existing_managed_paths`
  Evidence: before the fix -> `ERROR: test_init_sets_managed_paths` (KeyError); `test_init_keeps_existing_managed_paths` passed as a regression guard (setdefault)

## 2. Fix

- [x] 2.1 `check_panel` per design 1; 1.1 passes
  Evidence: `python3 -m unittest tests.test_check_change.PanelFormatTest` -> OK; infisical's prose panel.md -> `FAIL panel no findings in checklist format`
- [x] 2.2 Base-branch exemption config (design 4), `managed_paths` in tests-with-code and size, depth-agnostic default `test_globs` and `managed_paths: []` in config.yaml with comments; 1.2 passes
  Evidence: `python3 -m unittest tests.test_check_change.ExemptionTest` -> OK (4 tests, incl. `test_pr_cannot_grant_own_exemption`)
- [x] 2.3 `init.sh` sets the exact `managed_paths` list; 1.3 passes
  Evidence: `python3 -m unittest tests.test_init` -> OK; this repo's config keeps `managed_paths: []`
- [x] 2.4 Update the docs/lifecycle.md check table, the docs/security.md known gaps, and the adversarial-panel skill (`No findings.`, tag rules); run `scripts/sync-skills.sh`
  Evidence: `scripts/sync-skills.sh` -> `synced 3 skill(s)`; `grep -c managed_paths docs/lifecycle.md docs/security.md` -> 3, 1
- [x] 2.5 Run the full suite and `scripts/check-change.sh --stage hook`; record them as `Evidence:`
  Evidence: `python3 -m unittest discover -s tests` -> `Ran 52 tests ... OK`; `scripts/check-change.sh --stage hook --quiet` -> rc=0

## 3. Archive

- [x] 3.1 After archive, confirm `openspec validate --all --strict` passes with the merged `gate-checker` spec
  Evidence: `openspec validate --all --strict` -> `Totals: 2 passed, 0 failed`
