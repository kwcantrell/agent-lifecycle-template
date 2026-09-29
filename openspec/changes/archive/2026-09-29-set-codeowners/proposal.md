# Set code owners

Tier: 2
Tier reason: touches .github/ and scripts/ (high-risk paths); changes who must review lifecycle guardrails.
Approved-by: Kalen 2026-09-29

## Why

`.github/CODEOWNERS` still says `@OWNER`, a placeholder GitHub can't resolve. So the ruleset's
"require code owner review" protects nothing in this repo. The same file is also the source that
`scripts/init.sh` copies into target repos. Putting a real handle in it would make this repo's
owner the code owner of every repo the template installs into.

## What Changes

- This repo's `.github/CODEOWNERS` names `@kwcantrell` as the owner of the lifecycle paths.
- The installable CODEOWNERS moves to `scripts/templates/CODEOWNERS.tmpl`, keeping the `@OWNER` placeholder.
- `init.sh` renders the target's CODEOWNERS from that template with Python (no sed). The owner
  must be a valid `@user`, `@org/team` or email, and is checked before any file is written.
- `init.sh` never writes or edits CODEOWNERS when the target has one in `.github/`, the root or
  `docs/`. With no owner it skips the file and says so first in "Next steps".
- `init.sh` collects all inputs before writing, prompts only on a terminal, and `--dry-run`
  reports the CODEOWNERS outcome.
- Tests in `tests/test_init.py` cover every scenario in the spec delta.
- `docs/security.md` states the solo-owner bypass gap; `docs/lifecycle.md` Setup covers CODEOWNERS.

## Non-goals

- Changing which paths are owned.
- Adding reviewers or teams beyond `@kwcantrell`.
- Changing the ruleset (already applied with admin bypass on PRs).

## Impact

- `.github/CODEOWNERS`, `scripts/init.sh`, new `scripts/templates/CODEOWNERS.tmpl`, new `tests/test_init.py`,
  `docs/security.md`, `docs/lifecycle.md`. About 100 non-test lines, inside the 400-line budget.
