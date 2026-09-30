# ADR numbers are unique

Tier: 2
Tier reason: touches scripts/lib/check_change.py (high-risk path); adds a gate to every stage.

Approved-by: Kalen 2026-09-29

## Why

PR #8 (merged 19:57) and PR #9 (opened about 20:00, merged 20:01) each added a
`docs/decisions/0016-*.md`. Nothing checks ADR numbers, so both merged and "ADR 0016" became
ambiguous until PR #10 renumbered one. CI for #9 ran on GitHub's merge commit, which already
contained #8's 0016, so a duplicate check in CI would have caught it. When the base moves after CI
has run, though, only "require branches to be up to date" makes CI see the combined tree.

## What Changes

- **A new `adr` check.** Files in `docs/decisions/` named `NNNN-*.md` (extension in any case) must
  have unique numbers in the resulting tree: tracked files, plus untracked non-ignored ones locally.
  Other names are ignored, so targets with their own ADR naming aren't affected.
- **Stage-aware, like the YAML gate.** The `pr` stage (CI, which runs on GitHub's merge commit)
  fails on any duplicate. The `commit` and `hook` stages fail when the change touched one of the
  duplicated files, and only warn about duplicates already in the repo, so an adopted repo doesn't
  deadlock.
- **Docs.**
  - docs/lifecycle.md check table.
  - ADR 0018.
  - docs/security.md: "require branches to be up to date before merging" is recommended as a
    human-applied setting, noting that admins bypass it. Renumbering an ADR that's already merged is
    left to human review, as #10 did.

## Non-goals

- Gapless or sequential numbering.
- Comparing against a newer `origin/main` than the merge-base (dropped: CI's merge commit already
  catches the #8/#9 case, and the local version falsely failed on renames and silently missed on
  stale refs).
- Forbidding renames or deletions of merged ADRs (declined by agent pending the approver: #10 did
  exactly that, legitimately).

## Impact

- `scripts/lib/check_change.py` (about 25 lines), `tests/`, `docs/lifecycle.md`, `docs/security.md`,
  `docs/decisions/0018-adr-numbers-unique.md`.
