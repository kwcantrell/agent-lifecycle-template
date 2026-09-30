# Read git paths exactly in artifacts-first and size; renumber the duplicate ADR 0016

Tier: 2
Tier reason: touches scripts/ (high-risk path); the gate checker is the lifecycle's enforcement.

Approved-by: Kalen 2026-09-29

## Why

`archived-task-edits` (PR #8) made the shared changed-file list exact: NUL-separated, with rename
detection off. Two gates still parse git output of their own, and both misread paths.

**artifacts-first** splits `git diff-tree --name-only` output on whitespace, and git quotes
non-ASCII names. A plan commit holding `openspec/changes/<id>/a b.md` or `.../é.md` therefore fails,
reporting `b.md` or a quoted path as stray. This fails closed, but it rejects a legitimate plan
commit. Measured:
- `also has ['b.md']`
- `also has ['"openspec/changes/add-thing/\303\251.md"']`

**size** reads `git diff --numstat` line by line:
- **Moves:** it judges a move by one mangled entry, `{tests => src}/big.py`, counting only the
  content delta. Moving a 50-line file from an excluded `tests/` into `src/` and adding one line
  counts as **1** changed line (measured: `PASS size 1/10`), so source can enter the tree
  unmeasured.
- **Non-ASCII paths:** these come back quoted, so exclusion globs miss them. 50 lines added to
  `docs/é.md` count toward the budget, although `docs/**` is excluded.

Separately, PRs #8 and #9 each added an ADR numbered 0016:
- `0016-archived-task-edits.md`, from #8, merged first;
- `0016-config-files-must-parse.md`, from #9.

"ADR 0016" is now ambiguous.

## What Changes

- **artifacts-first** lists the first commit's paths with `-z`.
- **size** reads `--numstat -z -M`, which forces rename detection whatever the user's git config.
  It parses plain and rename records, and counts a move by where it lands:
  - between two counted paths: the content delta only, so a pure move costs 0;
  - from excluded to counted: the whole file, since it enters measured source;
  - from counted to excluded: the old file's lines, like a deletion;
  - between two excluded paths: 0.
- **ADR renumber:** `docs/decisions/0016-config-files-must-parse.md` becomes
  `0017-config-files-must-parse.md`, with its title updated and a note that it merged as 0016.
- **Docs:** ADR 0016 (archived-task-edits) records that the exact-path rule now covers every gate
  that reads git paths. `docs/lifecycle.md`'s size row says how moves count.
- Regression tests for each.

## Decisions (owner, 2026-09-29)

- **One PR** for the path fixes and the ADR renumber.
- **Moves: rename-aware counting**, not rename detection off. The panel measured the off option:
  every move would cost double its lines, so an 8-line move would fail a 10-line budget, and routine
  refactors would lean on `size-override`.

## Non-goals

- The rest of the size gate: untracked files, the budget, overrides, stages. Also its existing
  blind spots:
  - binary files count 0;
  - symlinks and gitlinks count 1;
  - evil merges are skipped, because artifacts-first ignores merge commits.
- Copy detection (`-C`), which is off by default and stays off.
- Rewriting yaml-parse-gate's archived records. Editing an archive beyond `tasks.md` counts as a
  second change on the branch, and archives are history.
- `rev-list` parsing, which prints SHAs.

## Capabilities

- Modified: `gate-checker`. "Changed paths are read exactly" extends to artifacts-first and size,
  with scenarios for each, including how moves count.

## Impact

- `scripts/lib/check_change.py`: about 25 lines (`check_artifacts_first`, `check_size`).
- `tests/test_check_change.py`: one new test class.
- Docs: the ADR rename and note, one line in ADR 0016, and one row in `docs/lifecycle.md`.
- On archive: `openspec/specs/gate-checker/spec.md`.
