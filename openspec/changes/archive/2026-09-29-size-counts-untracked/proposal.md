# Size counts untracked files

Tier: 2
Tier reason: touches scripts/lib/check_change.py (high-risk path); changes what the size gate counts.

Approved-by: Kalen 2026-09-29

## Why

The size gate counts `git diff --numstat <base>`, which leaves out untracked files. While building
adopt-installer, the gate reported 151 changed lines locally. After committing, it reported 577:
the new 419-line `scripts/lib/adopt.py` was invisible until then. The Stop hook and pre-commit run
before any commit, so an agent can build far past the budget without being told. CI counts it,
but only after the work is done.

## What Changes

- **Local runs count untracked files.** Outside CI, the size gate also counts untracked, non-ignored
  files as added lines, with the same exclusions as tracked changes. CI keeps counting committed
  diffs only, so build output a stack-setup step creates can't inflate it.
- **Counting matches git.** Paths are read with `-z`. Regular files only. A NUL byte in the first
  8000 bytes means binary, which isn't counted. Lines are counted as git does, streamed with an
  early stop once over budget. A symlink counts as 1 line.
- **The hook stage warns.** `size` joins the `hook` stage (Stop hook and pre-push) as a **WARN**,
  never a FAIL. The agent and pusher are told early, and the PR stage still enforces. An approved
  over-budget change isn't blocked locally.
- **Docs:** an ADR 0007 amendment, and the docs/lifecycle.md check table and scratch-file note.

## Non-goals

- Changing the budget or its exclusions.

## Impact

- `scripts/lib/check_change.py` (about 35 lines), `tests/test_check_change.py`, `docs/lifecycle.md`,
  `docs/decisions/0007-small-batches.md`.
