## 1. Tests first

- [x] 1.1 Write failing tests in `tests/test_check_change.py` (`GrandfatherTest`): `test_grandfathered_change_skips_change_gates` (asserts each of the 6 SKIPs and WARN for change), `test_grandfathered_risk_floor_warns`, `test_grandfathered_other_gates_still_run` (a failing command fails the run; tests-with-code runs), `test_grandfathered_needs_pr_declaration_in_ci`, `test_grandfathered_archive_path`, `test_new_change_reusing_id_not_grandfathered` (with hint), `test_pr_own_list_ignored` (base with and without a lifecycle block), `test_malformed_list_grandfathers_nothing` (missing, null, string), `test_grandfathered_plus_second_change_fails`
  Evidence: `python3 -m unittest tests.test_check_change.GrandfatherTest` before the fix -> `FAILED (failures=7)`; the 3 not-grandfathered cases passed as regression guards. With the checker stashed later -> 6 FAIL
- [x] 1.2 Write failing `test_tier0_change_dir_fails` (proposal `Tier: 0`, and PR body tier 0 over a change dir)
  Evidence: before the fix -> `FAIL: test_tier0_change_dir_fails`

## 2. Fix

- [x] 2.1 Merge main after PR #3 lands (this change extends its checker)
  Evidence: PR #3 merged (`gh pr view 3` -> MERGED); the branch re-created from main at `9f75c52` before the first commit
- [x] 2.2 Checker per design 1-7; add `grandfathered_changes: []` to config.yaml with the design 8 comment; 1.1 and 1.2 pass
  Evidence: `python3 -m unittest discover -s tests` -> `Ran 62 tests ... OK`
- [x] 2.3 ADR 0014; docs/lifecycle.md rows `change`, `risk-floor` and `size`, plus the "Grandfathering" subsection; the docs/security.md gaps
  Evidence: `ls docs/decisions/0014-grandfathered-changes.md`; docs/lifecycle.md rows change, risk-floor and size plus `### Grandfathering in-flight changes`; docs/security.md gap added
- [x] 2.4 Rehearse on a scratch copy of infisical: install commit on main, a list commit on main, the in-flight branch merges main, gates with a PR-body event -> `WARN change grandfathered`. No change to /home/spark/infisical
  Evidence: scratch clone of infisical, adopt-main at `e5886f4` + install + list, in-flight `d56dcc6^2` merged -> `WARN change grandfathered`, `WARN risk-floor ... scripts/backup.sh ...`, rc=0; no PR line -> `FAIL change ... declare Grandfathered: self-host-infisical`; after archive -> `WARN change ... archive/2026-09-29-self-host-infisical`. /home/spark/infisical unchanged (`status` 0 lines, still `b72d0aa`). Note: infisical has since archived this change itself, so history was used.
- [x] 2.5 Run the full suite and `scripts/check-change.sh --stage hook`; record them as `Evidence:`
  Evidence: `python3 -m unittest discover -s tests` -> OK (62); `scripts/check-change.sh --stage hook --quiet` -> rc=0

## 3. Archive

- [ ] 3.1 After archive, confirm `openspec validate --all --strict` passes
