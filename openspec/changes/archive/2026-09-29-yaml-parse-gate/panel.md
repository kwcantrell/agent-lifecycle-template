# Panel: yaml-parse-gate

Tier: 2 · Reviewers: assumption tester (A), failure and abuse (F), scope and simplicity (S), each a separate Sonnet subagent · Date: 2026-09-29

Findings are de-duplicated. All are resolved in the revised proposal, design, spec and tasks.
None were declined.

- [x] [major] F-M1: a hard FAIL on every YAML file in every stage deadlocks the Stop hook on pre-existing broken files the agent shouldn't touch. Resolved: design 5, where the commit and hook stages FAIL on touched files and WARN on untouched ones, and the PR stage FAILs on all. Test `test_preexisting_broken_warns_in_hook_fails_in_pr`.
- [x] [major] F-M2: `parse_exclude` is an unbounded bypass. Resolved: design 6 drops it.
- [x] [major] F-M3: "parses" isn't the real failure mode; a valid-YAML but wrong-shape pre-commit config also fails to load. Resolved: design 4 shape check; test `test_precommit_shape_checked`.
- [x] [major] F-M4 / A-M1: constructor-phase errors (ValueError, AttributeError), RecursionError and UnicodeDecodeError aren't YAMLError and would crash the checker. Evidence: `!!int abc` -> ValueError without a mark. Resolved: design 3, per-file `except Exception`; test `test_constructor_and_nesting_errors_fail_per_file`.
- [x] [major] S-M1 / A-M2: a base lacking `parse_exclude` yields None, losing the default or raising TypeError. Resolved: design 6, the key is dropped.
- [x] [major] S-M2: `parse_exclude` is speculative here (11 YAML files, no Helm). Resolved: design 6.
- [x] [major] A-M3: the Helm default glob misses `deploy/helm/<c>/templates/` and `chart/templates/`. Resolved: design 6, the limitation is recorded in ADR 0016.
- [x] [minor] A-m1: `git ls-files` returns tracked symlinks; a dangling one would raise. Resolved: design 1; test `test_symlinks_skipped`.
- [x] [minor] A-m2: duplicate keys are silently accepted. Resolved: listed as a non-goal and a possible follow-up.
- [x] [minor] A-m3: the assumptions table lacked loader-safety evidence. Resolved: rows added (python tags rejected, alias bomb about 1 ms).
- [x] [minor] F-m1: interaction with grandfathering and adoption wasn't stated. Resolved: design 7; adoption repos with pre-existing broken YAML get a WARN in hooks and a FAIL in the PR stage.
- [x] [minor] F-m2: default glob too narrow and too broad. Resolved: moot, since the key is dropped.
- [x] [minor] S-m3: installer impact wasn't stated. Resolved: design 8, no change.
- [x] [minor] S-m4: say why whole-repo scanning over changed-only. Resolved: design 5.
- [x] [minor] S-m5: docs/security.md exemption list and untracked-local test. Resolved: no new exemption key, so security.md is unaffected; test `test_untracked_checked_locally_not_in_ci`.
- [x] [minor] S-m6: budget fine (about 60 lines). Resolved: none needed.
