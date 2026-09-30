# Design: read git paths exactly in artifacts-first and size

Revised after the panel (see panel.md). Finding ids are in brackets.

## Context

`changed_files` and `exempt_archives` already read git output NUL-separated with `--no-renames`
(`archived-task-edits`). Two gates still parse git output of their own:
- `check_artifacts_first`:
  `git("diff-tree", "--no-commit-id", "--name-only", "-r", commits[0]).split()`
- `check_size`: `for line in git("diff", "--numstat", ctx.base).splitlines()`, then
  `line.split("\t", 2)`

`rev-list` prints SHAs. `untracked_lines(path, cap)` counts a working-tree file's lines the way
numstat does (1 for a symlink, 0 for binary or non-regular).

## Decisions

1. **artifacts-first: `-z`.** Add `-z` to `diff-tree` and split on NUL, dropping empty strings.
   - `diff-tree` never detects renames unless asked, even with `diff.renames=copies` [A: verified],
     so the list already has both sides.
   - `-z` also turns off quoting, so a non-ASCII name keeps its `openspec/changes/` prefix.
   - The stray check is unchanged.
2. **size: every count from git, with rename-aware moves** (owner decision; re-panel RF-NEG-COST, RA-4).
   Two numstat calls against the base:
   - `--numstat -z --no-renames`: one record per path, `added\tdeleted\tpath`. These are git's own
     counts, honouring `.gitattributes`. They are never negative, and binary reports `-`.
   - `--numstat -z -M`: only to find renames. A rename record is `added\tdeleted\t` (empty path),
     then `old` and `new` as the next two NUL fields. Plain records are one field. `-M` forces
     rename detection whatever `diff.renames` says.

   Cost:
   - Start from the `--no-renames` records: sum `added + deleted` for every path that isn't
     excluded (binary `-` counts 0, as today).
   - For each rename where **both** `old` and `new` are counted, replace the two sides' plain counts
     with the rename's own `added + deleted` (a pure move costs 0; a binary rename, `-`, costs 0).
   - Any other rename keeps its plain counts:
     - excluded to counted costs the new file's added lines;
     - counted to excluded costs the old file's deleted lines;
     - excluded to excluded costs 0.

   The parser walks the `-M` fields with an index: a record with an empty path field consumes the
   next two fields, so a binary rename can't shift the rest [RF-BIN-RENAME-PARSE]. Empty fields end
   the walk, so an empty diff gives 0 [A-2]. No working-tree file is read, so local and CI counts
   agree for committed and staged changes.
3. **ADR renumber.** `git mv docs/decisions/0016-config-files-must-parse.md
   docs/decisions/0017-config-files-must-parse.md`.
   - The heading becomes `# 0017: YAML files must parse`.
   - A note is added: "Merged as 0016 in PR #9, alongside `0016-archived-task-edits` from PR #8,
     and renumbered because #8 merged first. yaml-parse-gate's archived records use the old number
     and path."
4. **Rule and docs** [S-2, S-3].
   - ADR 0016 (archived-task-edits): its `Rule:` line gains "artifacts-first and size read git
     paths the same way (exact-git-paths)".
   - `docs/lifecycle.md`'s size row gains "A moved file counts by where it lands: its edits within
     counted source, the whole file when it crosses into or out of an exclusion".

## Accepted residuals

- **Stale paths in the archive:** yaml-parse-gate's archived `proposal.md` and `tasks.md` name
  `docs/decisions/0016-config-files-must-parse.md`, which no longer exists after the rename. The
  ADR's note maps it. No validator reads it [A-4, F-ADR-DANGLE].
- **Installed copies of the old ADR:** a repo that installed the template while 0016 was
  duplicated keeps its copy. The create-only installer then also adds 0017 on a re-install. That's
  harmless, and removing the stale copy is a human's call [F-ADR-DANGLE].
- **Existing size-gate blind spots**, now listed as non-goals [F-RESIDUAL-EVASION]:
  - binary files count 0;
  - symlinks and gitlinks count 1;
  - artifacts-first ignores merge commits.
- **Rename matching limits** [RF-SIMILARITY-DISCOUNT, RF-RENAME-LIMIT-FALLBACK, RA-2]:
  - A delete plus add that git scores at 50% or more similar costs its line delta, like an edit
    in place. Below that, it costs both files.
  - Past `diff.renameLimit`, inexact renames fall back to delete plus add. That overcounts (fails
    closed) and may differ between machines. `-l0` would remove the limit, at O(n²) cost, so it's
    not used.
- **Unstaged moves count twice locally** [RA-3, RF-LOCAL-CI-ASYMMETRY]. A plain `mv` that isn't yet
  staged shows as a deletion plus an untracked file, so the hook stage (which only warns) can
  overcount until `git add`. CI sees committed renames.
- **Copies** are not detected (`-C` stays off), so a copied file counts as a new file, which is
  conservative.

## Alternatives considered

- **Rename detection off** (`--no-renames`): the first draft. The panel measured every move costing
  twice its lines, so an 8-line move failed a 10-line budget [A-5, F-MOVE-DOUBLE]. The owner chose
  rename-aware counting.
- **Renumber `0016-archived-task-edits` instead.** Two live docs cite it, and it merged first.
  Rejected.
- **Separate PRs for the renumber and the code** [S-4]: the owner chose one PR.

## Assumptions

| Assumption | Command | Observed |
| --- | --- | --- |
| artifacts-first misreads a space | temp `Repo`; tier 2 change with `openspec/changes/add-thing/a b.md` in the first commit; `--only artifacts-first` | `FAIL ... also has ['b.md']` |
| artifacts-first misreads non-ASCII | same, with `é.md` | `FAIL ... also has ['"openspec/changes/add-thing/\303\251.md"']` |
| size undercounts a move out of an exclusion | base has 50-line `tests/big.py`; `git mv` to `src/big.py`, plus one line; budget 10 | `PASS size 1/10`; numstat shows `1 0 {tests => src}/big.py` |
| numstat quotes non-ASCII, so exclusions miss them | 50-line `docs/é.md`, budget 10 | numstat `50 0 "docs/\303\251.md"`; `FAIL size 50` |
| `-z -M` rename records, independent of `diff.renames` | `git -c diff.renames=false diff --numstat -z -M main` after two moves | `'0\t0\t\x00lib/a.py\x00lib/b.py\x001\t0\t\x00tests/big.py\x00src/big.py\x00'` |
| `diff-tree -z` prints raw, NUL-terminated names | `git diff-tree --no-commit-id --name-only -r -z HEAD` | `'docs/é.md\x00'` |
| `diff-tree` never detects renames (assumption tester) | commit moving `src/app.py` into `openspec/changes/…`, with `diff.renames copies` set | both paths listed |
| An empty diff yields `''` [A-2] | `git diff --numstat -z HEAD` on a clean tree | `''` |
| No live file cites the YAML ADR by number | `git grep -n 0016 -- . ':!openspec/changes/archive'` | `docs/lifecycle.md:52`, `docs/security.md:57` (both archived-task-edits) and the two ADR headings |
