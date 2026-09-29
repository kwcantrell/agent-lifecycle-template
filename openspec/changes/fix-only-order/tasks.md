## 1. Tests first

- [ ] 1.1 Write failing tests in `tests/test_check_change.py`: `test_only_order_does_not_change_results` (`approval,panel,change` and `change,approval,panel` both give PASS in the listed order), `test_only_without_change_still_resolves_it` (`approval,panel` gives PASS)
- [ ] 1.2 Write failing tests `test_change_failure_not_swallowed` (two change dirs, `--only approval`: `FAIL change`, approval blocked, rc 1), `test_unrelated_check_ignores_change_failure` (two change dirs, `--only build` with `build: true`: rc 0, no change line) and `test_pr_tier_without_change_does_not_crash` (PR body `Tier: 1`, no change dir, pr stage: no traceback, change FAIL)
- [ ] 1.3 Write failing tests `test_only_dedupes_names` (`change,change` prints once) and `test_only_rejects_unknown_names` (`bogus`, `""`: rc 2, lists valid names, no traceback)

## 2. Fix

- [ ] 2.1 In `main()`: parse and validate `--only`, resolve the change once up front, count and print a failing change when it or a `NEEDS_CHANGE` check was requested, and block `NEEDS_CHANGE` checks after a change FAIL; 1.1-1.3 pass
- [ ] 2.2 Run `scripts/check-change.sh --stage hook` and the full test suite, and record them as `Evidence:`

## 3. Archive

- [ ] 3.1 After archive, replace the placeholder `## Purpose` in `openspec/specs/gate-checker/spec.md`
