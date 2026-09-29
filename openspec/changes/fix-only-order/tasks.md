## 1. Tests first

- [x] 1.1 Write failing tests in `tests/test_check_change.py`: `test_only_order_does_not_change_results` (`approval,panel,change` and `change,approval,panel` both give PASS in the listed order), `test_only_without_change_still_resolves_it` (`approval,panel` gives PASS)
  Evidence: `python3 -m unittest tests.test_check_change.OnlyTest` before the fix -> `FAILED (failures=6)`, including `test_only_order_does_not_change_results (only='approval,panel,change')`
- [x] 1.2 Write failing tests `test_change_failure_not_swallowed` (two change dirs, `--only approval`: `FAIL change`, approval blocked, rc 1), `test_unrelated_check_ignores_change_failure` (two change dirs, `--only build` with `build: true`: rc 0, no change line) and `test_pr_tier_without_change_does_not_crash` (PR body `Tier: 1`, no change dir, pr stage: no traceback, change FAIL)
  Evidence: same run -> `FAIL: test_change_failure_not_swallowed`, `FAIL: test_pr_tier_without_change_does_not_crash`; `test_unrelated_check_ignores_change_failure` already passed (regression guard)
- [x] 1.3 Write failing tests `test_only_dedupes_names` (`change,change` prints once) and `test_only_rejects_unknown_names` (`bogus`, `""`: rc 2, lists valid names, no traceback)
  Evidence: same run -> `FAIL: test_only_rejects_unknown_names` x3; `test_only_dedupes_names` fails after adding its rc/Traceback asserts

## 2. Fix

- [x] 2.1 In `main()`: parse and validate `--only`, resolve the change once up front, count and print a failing change when it or a `NEEDS_CHANGE` check was requested, and block `NEEDS_CHANGE` checks after a change FAIL; 1.1-1.3 pass
  Evidence: `python3 -m unittest discover -s tests` -> `Ran 39 tests ... OK`; `scripts/check-change.sh --only bogus` -> `unknown check ['bogus']; valid checks: ...`, rc=2
- [x] 2.2 Run `scripts/check-change.sh --stage hook` and the full test suite, and record them as `Evidence:`
  Evidence: `scripts/check-change.sh --stage hook --quiet` -> rc=0; `--only approval,panel,change` -> PASS approval, PASS panel, PASS change

## 3. Archive

- [ ] 3.1 After archive, replace the placeholder `## Purpose` in `openspec/specs/gate-checker/spec.md`
