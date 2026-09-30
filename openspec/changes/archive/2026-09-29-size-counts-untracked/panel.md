# Panel: size-counts-untracked

Tier: 2 · Reviewers: assumption tester (A), failure and abuse (F), scope and simplicity (S), each a separate Sonnet subagent · Date: 2026-09-29

Findings are de-duplicated. All are resolved in the revised proposal, design, spec and tasks.
None were declined.

- [x] [major] S-M2 / F-M2 / A-M1: a hard FAIL for size at the hook stage traps the agent. An approved override lives only in the PR label, the Stop hook can't see it, and its 3-strike give-up teaches agents to ignore hook output. Evidence: stop-check.sh `n > 3` then exit 0; `LIFECYCLE_OVERRIDE` only read from env. Resolved: design 3, where the hook stage WARNs and the PR stage enforces; test `test_hook_stage_warns_on_size`.
- [x] [major] F-M1: pre-push runs `--stage hook`, so approved over-budget branches would fail every push, pushing humans to `--no-verify` (which skips all hooks). Evidence: `.pre-commit-config.yaml` lifecycle-push. Resolved: design 3 (WARN).
- [x] [major] S-M1: adding size to the hook stage is a behaviour change that needs an ADR. Resolved: design 5, the ADR 0007 amendment (task 2.2).
- [x] [major] S-M3: docs incomplete (the hook column of the size row, ADR 0007). Resolved: task 2.2.
- [x] [major] A-M2: non-ASCII names come back C-quoted without `-z`; `open()` fails. Evidence: `"\303\251.txt"`. Resolved: design 1 (`-z`); test `test_size_untracked_odd_names`.
- [x] [major] A-M3: in CI, un-ignored build output from stack setup would be counted, flipping PASS to FAIL. Evidence: 9000-file tree -> 450000 lines. Resolved: design 1 (no untracked scan in CI); test `test_size_ci_ignores_untracked`.
- [x] [major] F-M3: untracked scratch files (logs, notes) count locally. Resolved: design 4; the hook only warns, and the docs say to ignore or exclude them.
- [x] [minor] A-m4: line counting must match git (CR-only, no trailing newline). Evidence: `git diff --no-index --numstat` values. Resolved: design 2's formula; test `test_size_counts_last_line_without_newline`.
- [x] [minor] A-m5: git's binary window is 8000 bytes, and whole-file reads risk huge files. Resolved: design 2 (8000 bytes, streamed, early stop).
- [x] [minor] A-m6 / F-m3: skipping symlinks breaks parity with git, which counts a staged symlink as 1. Resolved: design 2 (symlink = 1).
- [x] [minor] F-m1: unbounded reads, FIFOs and devices could hang the hook. Resolved: design 2 (regular files only, streamed with a cap).
- [x] [minor] F-m2: gitignoring new files or `test_*` names evades the local count. Resolved: stated in the ADR 0007 consequences. Ignored files never reach CI; `test_*` predates this change.
- [x] [minor] S-m1: the scenario-to-test mapping was implicit, and symlinks had no test. Resolved: task 1.1 names a test per scenario, and the symlink case goes in `test_size_skips_excluded_ignored_binary_untracked`.
- [x] [minor] S-m2: unreadable or race-prone files were unspecified. Resolved: design 2 (skip on `OSError`).
