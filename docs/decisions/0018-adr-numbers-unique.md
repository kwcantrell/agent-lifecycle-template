# 0018: ADR numbers are unique

- Date: 2026-09-29
- Status: Accepted
- Rule: check `adr`

## Context

PR #8 (merged 19:57) and PR #9 (opened about 20:00, merged 20:01) each added a
`docs/decisions/0016-*.md`. Nothing checked ADR numbers, so "ADR 0016" became ambiguous until
PR #10 renumbered the later one to 0017.

## Decision

Files in `docs/decisions/` named `NNNN-*.md` must have unique numbers in the resulting tree. The
PR stage fails on any duplicate. It runs on GitHub's merge commit, which for #9 already contained
#8's 0016. The commit and hook stages fail when the change touched a duplicated file, and warn on
duplicates already in the repo, so adopted repos don't deadlock.

## Evidence

- The tree at #9's merge (`a9b9130`) under this check:
  `FAIL adr duplicate ADR numbers ... 0016: 0016-archived-task-edits.md, 0016-config-files-must-parse.md`.
- The adr-numbers panel (12 findings).

## Consequences

- A collision whose base moves after CI ran is only caught by requiring up-to-date branches, which
  is documented in docs/security.md as optional, and which the admin bypass skips.
- Renumbering an ADR that's already merged isn't forbidden. #10 did it correctly, with a note, under
  human review. An agent could "fix" a collision by renumbering the wrong ADR, and review is the
  control.
