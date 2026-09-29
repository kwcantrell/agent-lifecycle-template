# Panel: fix-only-order

Tier: 2 · Reviewers: assumption tester (A), failure and abuse (F), scope and simplicity (S), each a separate Sonnet subagent · Date: 2026-09-29

Findings were de-duplicated across reviewers, and each id shows who raised it. All are resolved
in the revised proposal, design, spec and tasks. None were declined.

- [x] [major] F-M1 / A-M1 (F, A): when `change` isn't in `--only`, its FAIL (two change dirs, missing `Tier:`, PR/proposal tier mismatch) is discarded. Dependent checks then report SKIP and the run exits 0, which is the same false-pass class as the bug. Evidence: check_change.py:150-167 early returns, :382-383 result dropped, :180 SKIP on falsy tier. Resolved: design 2. Spec requirement "A change failure is never hidden"; test `test_change_failure_not_swallowed`.
- [x] [major] A-M2 (A): the spec said `change` "prints once", but `--only change,change` prints it twice. Evidence: `scripts/check-change.sh --only change,change` -> two `PASS change` lines. Resolved: design 4 (de-duplicate); test `test_only_dedupes_names`.
- [x] [major] A-M3 (A): behaviour when `change` isn't requested was unspecified and untested. `--only approval,panel` only works today because of the pre-call. Resolved: design 1; scenario "Change not requested"; test `test_only_without_change_still_resolves_it`.
- [x] [major] Self-check during revision: `release.yml:29` runs `--only build`. Under the first revision, a `change` FAIL (every archived change looks in flight in a shallow tag checkout) would have failed every release. Evidence: `grep -n -- --only .github/workflows/*.yml` -> `release.yml:29`. Resolved: design 2 now counts the failure only when `change` or a dependent is requested; test `test_unrelated_check_ignores_change_failure`.
- [x] [minor] F-m1 (F): after a `change` FAIL, dependents run on a half-set context and give misleading results. Resolved: design 3 (dependents blocked).
- [x] [minor] F-m3 (F): a PR body `Tier: 1` with no change dir makes `check_approval` raise AttributeError. Evidence: check_change.py:182 `ctx.change_dir / "proposal.md"` with change_dir None. Resolved: design 3; test `test_pr_tier_without_change_does_not_crash`.
- [x] [minor] A-m2 (A): unknown or whitespace names crash with KeyError, and `--only ""` silently runs the full stage. Evidence: `--only bogus` -> `KeyError: 'bogus'`. Resolved: design 4 (trim, exit 2 with the valid names); test `test_only_rejects_unknown_names`.
- [x] [minor] S-m1 (S): the new `gate-checker` capability will be archived with a placeholder Purpose, and no task covered it. Resolved: task 3.1.
- [x] [minor] S-m2 (S): the test covered only one order. Resolved: task 1.1 covers two orders and 1.1 covers change omitted.
- [x] [minor] S-m3 / A-m1 (S, A): the repro cited the merged set-codeowners branch. Resolved: the design table cites this branch, and the tests reproduce in temp repos.
- [x] [minor] S-m4 (S): the size estimate was off. Resolved: the proposal now says about 25 lines, after the added scope.
- [x] [minor] F-m2 / F-m4 (F): no new exit-code or exception surface for CI and hook callers, which use `--stage`. Informational; confirmed in the design table. No change needed.
