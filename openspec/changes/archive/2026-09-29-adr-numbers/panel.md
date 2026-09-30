# Panel: adr-numbers

Tier: 2 · Reviewers: assumption tester (A), failure and abuse (F), scope and simplicity (S), each a separate Sonnet subagent · Date: 2026-09-29

Findings are de-duplicated. One major is declined by the agent pending the approver's call.

- [x] [major] S-M1: comparing against the latest base adds a second, env-dependent code path, while the duplicate check on CI's merge commit already catches #8/#9. Evidence: design (first draft) decision 2. Resolved: design 4, dropped.
- [x] [major] A-M1: the latest-base check false-fails a slug-only rename (`0016-a` to `0016-b`), because `--no-renames` lists the new path as added. Evidence: throwaway repo repro. Resolved: design 4 (dropped); design 2 counts the resulting tree only; test `test_renames_pass`.
- [x] [major] F-M3: the local latest-base check silently misses on a stale `origin/main`, and skipped silently in CI. Resolved: design 4 (dropped).
- [x] [major] F-M2: adopted repos with pre-existing duplicate numbers would deadlock the Stop hook. Resolved: design 3, where untouched duplicates warn at commit and hook and fail at pr; test `test_preexisting_duplicate_warns_in_hook_fails_in_pr`.
- [x] [major] S-M2: the ruleset setting is external scope. Resolved: design 5, documented only.
- [x] [major] F-M1: an agent could "fix" a collision by renumbering the merged ADR. Declined by agent pending the approver: #10 did exactly that, legitimately, under human review. Forbidding it would block the right fix; the gap is stated in ADR 0018.
- [x] [minor] F-m1: strict mode doesn't bind the admin bypass. Resolved: design 5, the caveat is documented.
- [x] [minor] F-m2: the pattern missed `.MD`; the `0000` template and untracked files were unspecified. Resolved: design 1; test `test_other_naming_ignored`.
- [x] [minor] A-m1: rename cases untested. Resolved: `test_renames_pass` covers a slug rename and renumbering one's own ADR.
- [x] [minor] A-m2: `ls-tree` output and a missing directory. Resolved: moot (no ls-tree); `ls-files` on a missing dir prints nothing.
- [x] [minor] A-m3: CI's fetch of origin/main was unverified. Resolved: moot (no latest-base comparison).
- [x] [minor] S-m1: simplest form is the duplicate check only. Resolved: adopted, plus stage-awareness from F-M2.
