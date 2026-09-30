# Panel: grandfather-changes

Tier: 2 · Reviewers: assumption tester (A), failure and abuse (F), scope and simplicity (S), each a separate Sonnet subagent · Date: 2026-09-29

This change replaces the auto-grandfathering part of the withdrawn `safe-adoption` draft, whose
panel found 4 critical issues (inputs kept for A2). Findings below are de-duplicated. One minor
is declined by the agent with a reason, pending the human's call at approval.

- [x] [major] A-M1: `with_base_exemptions` returns the PR's own config on every "no base lifecycle" path (no base, `git show` fails, no block), so listing the key in `EXEMPTION_KEYS` would leak the PR's list. Evidence: `git show accurate-gates:scripts/lib/check_change.py` -> `if not base: return cfg`, `if not isinstance(base_lc, dict): return cfg`. Resolved: design 1 uses its own `base_grandfathered` read, which returns `[]` on every such path; test `test_pr_own_list_ignored`.
- [x] [major] A-M2 / F-M3: a missing, null or string value could raise, or substring-match (`'leg' in 'legacy'`). Evidence: `python3 -c "print('leg' in 'legacy')"` -> True. Resolved: design 1 normalizes to a list of strings; test `test_malformed_list_grandfathers_nothing`.
- [x] [major] A-M3: base is the merge-base, so a branch that hasn't merged main isn't grandfathered and gets a bare Tier FAIL. infisical needs two sequential PRs. Evidence: infisical main has no lifecycle block (`grep -c lifecycle` -> 0). Resolved: design 7 adds a hint, design 8 documents the flow, and task 2.4 rehearses both PRs.
- [x] [major] F-M1: two-step self-grandfathering: merge a bare change dir in a tier 0 PR (no approval needed), then list it. Evidence: accurate-gates check_change passes tier 0 with a change dir; check_approval SKIPs at tier 0. Resolved: design 3 fails tier 0 with a change dir; test `test_tier0_change_dir_fails`.
- [x] [major] F-M2: skipping risk-floor lets a grandfathered branch edit scripts/, config or workflows silently. Evidence: NEEDS_CHANGE includes risk-floor. Resolved: design 6 makes risk-floor WARN with the paths; test `test_grandfathered_risk_floor_warns`; stated gap.
- [x] [major] S-M1: one test for seven outcomes; the claim that tests-with-code still runs was untested. Resolved: task 1.1 asserts each SKIP, plus `test_grandfathered_other_gates_still_run`.
- [x] [major] S-M2: cut archive-path support. Declined by agent pending the human's approval: without it a grandfathered change fails every gate on its archive PR, so infisical's change could never finish under the lifecycle. The exposure is stated in docs/security.md instead.
- [x] [minor] F-m1: the WARN is invisible under `--quiet` (hooks) and on green CI. Resolved: design 5 requires `Grandfathered: <id>` in the PR body in CI; test `test_grandfathered_needs_pr_declaration_in_ci`.
- [x] [minor] F-m2: a grandfathered branch has unbounded scope; one touching a second change dir needs a test. Resolved: stated as a known gap; test `test_grandfathered_plus_second_change_fails`.
- [x] [minor] A-m1: a shallow clone has no base, so nothing qualifies (fails closed). Resolved: stated in design 2; cat-file runs with output captured.
- [x] [minor] A-m2: any archive dir for a listed id qualifies while the base has the id. Resolved: added to docs/security.md known gaps.
- [x] [minor] A-m3: in `main()` the grandfathered branch must precede the `change_failed` branch, and size needs its own handling. Resolved: design 6.
- [x] [minor] S-m3: the "no base lifecycle" special case looked redundant. Resolved: kept, because the adoption case (a repo with change dirs but no lifecycle block) is exactly where it matters; covered by `test_pr_own_list_ignored`.
- [x] [minor] S-m4: docs tasks didn't name the check-table rows or the config comment. Resolved: design 8 and task 2.3 name them.
- [x] [minor] S-m5: no tests for "PR-body Tier ignored" or "one change per branch still applies". Resolved: the latter is `test_grandfathered_plus_second_change_fails`; the former is asserted inside `test_grandfathered_needs_pr_declaration_in_ci`.
- [x] [minor] S-m6: task 2.4 must not mutate another repo. Resolved: task 2.4 runs on a scratch copy only.
- [x] [minor] S-m7: budget about 60 lines, well under 400. Resolved: none needed; the proposal is updated.
