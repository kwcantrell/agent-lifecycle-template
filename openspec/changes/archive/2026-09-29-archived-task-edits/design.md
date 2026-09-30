# Design: don't count tasks.md-only edits to existing archives as a change

Revised after the panel (see panel.md). Finding ids are in brackets.

## Context

`check_change` collects every change directory touched by `ctx.changed`, archived or not
(`check_change.py:180-187`). It fails on more than one. With exactly one, it reads that directory's
`Tier:` line.

Archives are counted on purpose: a branch that archives its own change still resolves it, and the
grandfathering scenario "Archive of a grandfathered change" depends on that. `ctx.changed` comes from
`changed_files`, which parses `git diff --name-only`, `--cached` and `ls-files --others` output with
`.split()`. It is read by:
- `check_change`;
- `risk-floor` (`:226`);
- `tests-with-code` (`:339-340`).

## Decisions

1. **Exact changed paths, for every gate.** [F-1, F-2, A-1]
   - `changed_files` runs each git command with `-z` and splits on NUL.
   - The two `git diff` calls add `--no-renames`, so a move lists the old path and the new path.
   - `risk-floor` then sees a high-risk file moved out of its directory, which today it misses.
   - `tests-with-code` sees a moved source file's old path, and treats it like a deletion, as it
     already treats deletions.
   - `size` is unaffected: it uses its own `--numstat` call.
2. **The exemption, from raw records.** A new helper `exempt_archives(base)`:
   - Returns the set of archive directories that pass all of these, and nothing when there is no base:
     - the name matches `^\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]*$` [F-9];
     - `on_base(base, dir)` holds;
     - the directory's records in `git diff --raw --no-renames -z <base>` (base against the working
       tree, which covers committed, staged and unstaged changes) are exactly one record: status `M`,
       path `<dir>/tasks.md`, both modes `100644` [F-3, A-5];
     - no untracked file lies under the directory (`ls-files --others -z`).
   - `check_change` drops these directories before the "one change per branch" count. The rest of
     `check_change` is unchanged.
3. **The note on every result.** [S-4, A-2]
   - `check_change` becomes a thin wrapper around the existing body, renamed `_check_change`.
   - It appends `; not counted: tasks.md-only edits to existing archive(s) <names>` to whatever
     message the body returns: PASS, WARN or FAIL.
   - Names can't carry control characters or workflow-command text, because only pattern-matching
     names are exempt [F-9].
   - All stages call the same function, so `commit`, `hook` and `pr` all show it [F-6].
4. **No base, no exemption.**
   - `on_base` is false without a base, so a shallow or fresh checkout counts every archive, as today.
   - A branch cut from an old commit is also conservative: archives created after its merge-base are
     counted [F-7].
   - `release.yml` runs `--only build` and needs no change context.
5. **Grandfathered ids.** [F-5]
   - A tasks-only edit to `archive/<date>-<id>` for a grandfathered id is exempt like any other: tier
     0, no `Grandfathered:` line needed.
   - This is intended. Grandfathering exists so an in-flight change can finish, and an exempt edit is
     not a change.
   - `docs/security.md`'s grandfathering bullet is updated to match.
6. **Record the rule.** [S-2]
   - ADR 0016 records the incident (autologger-2: 26 tasks in six archives), the bounds, and the residual.
   - `docs/security.md` gains the false-tick residual [F-4, S-1].
   - `docs/lifecycle.md`'s `change` row gains the exemption.

## Owner decisions (2026-09-29)

- **Approach: this exemption**, over the alternative of skipping `--archived` validation for
  pre-adoption archives [S-3].
- **False ticks: documented residual** [F-4]. A tier 0 PR can tick archived tasks that weren't done,
  or edit their `Evidence:` lines. Controls:
  - the `change` message lists every exempted archive;
  - CODEOWNERS covers `openspec/changes/`, both in this repo and in the `CODEOWNERS.tmpl` that
    init.sh renders;
  - a repo that keeps its own CODEOWNERS is told by init.sh to add `/openspec/changes/` [S-1];
  - `docs/security.md` records it.

## Alternatives considered

- **Exempt only pure checkbox flips.** Too narrow: an honest edit annotates why a task is ticked
  without being done. Rejected.
- **Exempt any edit to an existing archive.** It would let a tier 0 PR rewrite archived decisions.
  Rejected.
- **Skip `--archived` for pre-adoption archives**, via a base-read list like `grandfathered_changes`.
  No history edits, and no tier 0 path to them. But it needs a new config key, and it leaves archives
  that fail validation in the tree permanently. Rejected by the owner.
- **Document a workaround only**, e.g. commit the edits straight to main. It needs a ruleset bypass,
  which `docs/security.md` treats as a hole. Rejected.
- **Grandfather each archive.** It covers one in-flight change per branch, and still counts it as the
  branch's change. Rejected.

## Assumptions

| Assumption | Command | Observed |
| --- | --- | --- |
| Two tasks.md-only archive edits fail today | temp repo from `tests/test_check_change.py` `Repo`; base has two archives; branch edits both `tasks.md`; `--only change` | `FAIL change one change per branch; found ['openspec/changes/archive/2026-01-01-old1', 'openspec/changes/archive/2026-01-02-old2']` |
| One such edit fails too | same, one archive | `FAIL change .../2026-01-01-old1/proposal.md must declare `Tier: 0\|1\|2`` |
| `.split()` breaks paths with spaces [F-1] | temp repo; add `<archive>/tasks.md smuggled.txt`; split `git diff --name-only --cached main` | `['.../tasks.md', '.../tasks.md', 'smuggled.txt']` |
| Renames hide the old path [F-2] | `git mv <archive>/proposal.md moved.md`; `git diff --name-only main` versus `--no-renames` | `moved.md .../tasks.md` versus `moved.md .../proposal.md .../tasks.md` |
| Raw records give status and modes, NUL-separated | `git diff --raw --no-renames -z main` in that repo | `:100644 100644 ... M\|.../tasks.md\|`; a symlink swap gives `:100644 120000 ... T\|.../tasks.md\|` |
| `on_base` works on directories [A-4] | `git cat-file -e main:<archive dir>` (assumption tester) | rc 0 |
| Nothing parses the `change` message [A-3] | `grep -rn "no change dir\|tier 0 (\|found \[" tests scripts docs .github .claude AGENTS.md` (assumption tester) | only the producer |
| Only `check_change` builds the change-dir set | `grep -n "dirs = \|ctx.change_dir = " scripts/lib/check_change.py` | lines 180, 187, 192, all in `check_change` |
| Only release.yml uses `--only`, for build | `grep -rn -- --only .github/workflows/*.yml` | `release.yml:29: scripts/check-change.sh --only build` |
| This repo's CODEOWNERS covers `openspec/changes/` | `grep changes .github/CODEOWNERS` | `/openspec/changes/      @kwcantrell` |
| The real case | `git diff --name-only 794c107 0ea7b39 -- openspec/changes/archive` in autologger-2 | six archives, each only `tasks.md` |
