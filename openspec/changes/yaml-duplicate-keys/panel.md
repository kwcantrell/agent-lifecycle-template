# Panel: yaml-duplicate-keys

Tier: 2 · Reviewers: assumption tester (A), failure and abuse (F), scope and simplicity (S), each a separate Sonnet subagent · Date: 2026-09-29

Findings are de-duplicated. All are resolved in the revised proposal, design, spec and tasks.
None were declined.

- [x] [major] F-M1: the pr stage would hard-fail untouched files with pre-existing duplicates, with no exclusion list, blocking adopted repos (Ansible only warns on duplicate keys). Evidence: check_change.py `strict = ctx.stage not in ("commit","hook")`. Resolved: design 4, where only duplicates introduced relative to the merge-base fail and inherited ones warn; test `test_inherited_duplicate_only_warns`.
- [x] [major] F-M2: a one-line edit to a file with an old duplicate would block the commit. Resolved: design 4 (same mechanism).
- [x] [major] S-M1: the docs/lifecycle.md yaml row would be wrong. Resolved: design 6, task 2.2.
- [x] [minor] S-m1: ADR 0017 edit vs a new ADR. Resolved: design 6, a dated amendment (same rule).
- [x] [minor] S-m2: the nested and boolean cases were bundled, and `1` vs `"1"` was untested. Resolved: `test_duplicate_equality_and_tags` covers the pass case too.
- [x] [minor] S-m3 / F-m1 / A-m4: equality is Python equality (`1`/`1.0`/`true`, `null`/`~`), not just booleans, and messages showed `True` for `on`. Resolved: design 1 (key as written) and design 2 (stated).
- [x] [minor] S-m4: pin the `super()` signature and the error line. Resolved: design 1.
- [x] [minor] F-m2: performance and DoS. Resolved: design 1; the cache means no double cost, and files over 1 MiB are already skipped.
- [x] [minor] F-m3: tagged mappings are checked, and unhashable keys behave as today. Resolved: design 1 and 5.
- [x] [minor] A-m1: two explicit `<<` keys aren't flagged. Resolved: design 3, where merge keys are exempt by design.
- [x] [minor] A-m2: an alias key reports the anchor's line. Resolved: design 1 states the limitation.
- [x] [minor] A-m3: the unhashable-key skip was dead code. Resolved: design 1, no special case.
- [x] [minor] A-m5: regression tests for verified-safe cases. Resolved: tagged mapping in `test_duplicate_equality_and_tags`; merge list in `test_merge_keys_exempt`.
