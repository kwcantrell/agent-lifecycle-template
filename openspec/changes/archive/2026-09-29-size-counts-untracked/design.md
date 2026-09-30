# Design: size counts untracked files

Revised after the panel (see panel.md).

## Decisions

1. **Untracked files count locally, never in CI.** When `ctx.in_ci` is false, `check_size` adds
   untracked, non-ignored files from `git ls-files -z --others --exclude-standard`, split on NUL
   so spaces and non-ASCII names work. The exclude list is the same as for tracked changes: tests,
   `managed_paths`, `size_exclude`, `openspec/**`. CI skips the scan, since its checkout has no
   untracked files except build output from stack setup. [A-M2, A-M3]
2. **Counting parity with git numstat.**
   - A symlink counts as 1 line, as git counts a staged symlink.
   - Anything that isn't a regular file (FIFO, device, directory entry) is skipped, as is a file
     that can't be read (`OSError`).
   - A NUL byte in the first 8000 bytes means binary, which isn't counted.
   - Lines = `count(b"\n")`, plus 1 if the file is non-empty and doesn't end in `\n`. This matches
     git for LF, CRLF, CR-only, a missing final newline, empty and blank-only files.
   - Reading streams in 1 MiB chunks, and stops as soon as the running total passes the budget, so
     a huge file costs at most budget-plus-one lines of reading.

   [A-m4, A-m5, A-m6, F-m1, F-m3]
3. **WARN in the hook stage.** `ctx.stage` is set in `main()`. At the `hook` stage, an over-budget
   size returns WARN "N changed lines > budget (the PR gate enforces; split, or ask the human for
   `size-override`)". The `pr` stage keeps FAIL. So the Stop hook never loops on size, and
   pre-push never forces `--no-verify` for an approved override, while the agent is still told.
   [S-M1, S-M2, F-M1, F-M2, A-M1]
4. **Scratch files.** Untracked notes and logs count locally. Because the hook only warns, they
   can't block anyone. docs/lifecycle.md says to gitignore them or add them to `size_exclude`.
   [F-M3]
5. **ADR 0007 amendment.** The Decision gains: "Locally the count includes untracked files and
   the hook stage only warns; the PR stage enforces." Consequences note the `test_*` naming
   loophole, which predates this change. [S-M3, F-m2]

## Assumptions

| Assumption | Command | Observed |
| --- | --- | --- |
| numstat omits untracked and includes staged-new files | panel repro | untracked: nothing; staged: counted; no double count |
| `ls-files --others` lists files inside untracked dirs | panel repro | `new/deep/nonl.txt` |
| Without `-z`, non-ASCII names come back quoted | panel repro | `"\303\251.txt"` |
| git's line counts | `git diff --no-index --numstat /dev/null <f>` for CR-only, no trailing newline, CRLF, empty, blank | `1`, `2`, `2`, `0`, `3` |
| git's binary window is 8000 bytes | a NUL at byte ~10000 -> text | `5001 0` |
| A staged symlink counts as 1 | `git add lnk; git diff --numstat` | `1 0 lnk` |
| Pre-push and Stop both run the hook stage | `.pre-commit-config.yaml` lifecycle-push; stop-check.sh | `--stage hook` |
