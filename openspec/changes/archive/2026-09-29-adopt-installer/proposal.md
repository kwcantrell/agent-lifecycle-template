# Adopt installer

Tier: 2
Tier reason: touches scripts/ (init.sh, a new scripts/lib/adopt.py); changes how the lifecycle installs into repos with existing agent guidance.

Approved-by: Kalen 2026-09-29

## Why

The infisical dry-run showed that init.sh half-installs into a repo with its own lifecycle:
settings.json is skipped but the hooks are copied, so they're unwired; the config merge re-dumps the
file and appends contradictory guidance; AGENTS.md and CLAUDE.md are skipped. Two designs that
merged into the repo's existing files drew 6 critical findings between them:
- a config append that corrupts silently;
- a crash after partial writes;
- gitignored files overwritten with no copy for git to restore;
- plan-to-apply tampering;
- a recovery command that misses files;
- `openspec init` writing between plan and apply.

The approver chose "propose, don't merge": the installer never modifies an existing file.

## What Changes

- **One installer process, create-only.** A new `scripts/lib/adopt.py install` does all the
  writing that init.sh did: copies, CODEOWNERS, skills and the fresh config.
  - It creates only paths that don't exist on the filesystem (gitignored files count), file by
    file.
  - It never edits, replaces or deletes an existing file, and never writes outside the target's
    real path.
  - The target's own `sync-skills.sh` never runs. The lifecycle skills are copied into
    `.agents/skills/<name>` only where absent.
- **Proposals for existing files.** For an existing AGENTS.md, CLAUDE.md, `.claude/settings.json`
  or `openspec/config.yaml`, it writes what a human should merge into `.lifecycle-adoption/`,
  with a `README.md` checklist:
  - a proposed settings.json;
  - a config snippet with the missing lifecycle sections;
  - the AGENTS.md and CLAUDE.md blocks, stating that the lifecycle gates win on conflict.

  The folder ignores itself (`.gitignore` of `*`), so the gates don't see it and it isn't
  committed by accident.
- **Risks reported up front.** These are listed first:
  - `defaultMode: bypassPermissions`, `disableAllHooks`, `allowUnsandboxedCommands`,
    `sandbox.enabled: false`, and bare-tool or `*` allow rules;
  - hooks installed but not wired;
  - hook scripts the target already has that differ from the template. The proposal won't wire
    those.
- **`openspec init` only when safe.** It runs only when the target has no `openspec/` and none of
  the files OpenSpec generates. Otherwise the checklist tells the human to run it.
- **A validated undo.** Each created file and directory is recorded in
  `.lifecycle-adoption/MANIFEST` after it's created. `adopt.py undo` checks every line before
  removing anything: relative, no `..`, not `.git`, inside the target. It removes files, then
  empty directories only. init.sh prints the undo command on success and on failure.
- **Target text is shown as data.** Control characters are stripped from echoed target strings,
  and the README says the proposals are for a human to review; agents must not apply them.
- In-flight changes are printed with the grandfathering steps (ADR 0014).

## Non-goals

- Editing any existing file automatically.
- Updating an existing install to a newer template version.

## Impact

- New `scripts/lib/adopt.py` (about 190 lines: install, proposals, risks, undo), `scripts/init.sh`
  (its copy loop, re-dump merge, CODEOWNERS render and sync-skills call move into adopt.py:
  about 90 lines deleted and 30 added),
  `tests/test_adopt.py`, `tests/test_init.py`, ADR 0015, `docs/lifecycle.md`, `docs/security.md`,
  `README.md`, and `openspec/config.yaml` (lint covers `scripts/lib/*.py`). About 310 changed lines, deletions counted.
