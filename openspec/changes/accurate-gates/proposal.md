# Accurate gates

Tier: 2
Tier reason: touches scripts/ and openspec/config.yaml (high-risk paths); changes what the panel, tests-with-code and size gates accept.

Approved-by: Kalen 2026-09-29

## Why

The infisical dry-run (build plan, 2026-09-29) found three gates that give false results:

- **Panel gate is blind to other formats.** infisical's panel.md is prose and tables, with
  critical findings discussed 7 times and no checklist items. The gate looks only for
  `- [ ] [critical]`, finds none, and reports PASS.
- **Nested test folders aren't tests.** The default `test_globs` match `tests/` only at the
  root, so infisical's `scripts/tests/*.sh` count as source, and tests-with-code fails falsely.
- **The template's own files count against the target.** `init.sh` installs
  `scripts/check-change.sh`, `scripts/sync-skills.sh`, `scripts/lib/check_change.py` and
  `.claude/hooks/*`. In a target they are vendored code, yet they trip tests-with-code (and count
  toward the size budget) on the install PR and on every template update.

## What Changes

- **Panel format is enforced.** Findings are top-level `- [ ]`/`- [x]` items whose first token is
  `[critical]`, `[major]` or `[minor]`. The gate fails in four cases:
  - there are no findings and no `No findings.` line;
  - an item is untagged or mis-tagged;
  - a critical is still open;
  - a ticked critical or major lacks `Resolved:` or `Declined`.

  Fenced code and HTML comments are ignored, and nested sub-bullets are not findings.
- **Test folders count at any depth**, via the default `test_globs` (`**/test/**`, `**/tests/**`, `**/__tests__/**`).
- **`lifecycle.managed_paths`** lists the exact files the lifecycle installs. tests-with-code and
  size ignore them. This repo keeps it empty; `init.sh` sets it for targets, and keeps a target's
  own value if it has one.
- **Exemptions can't be granted by the PR that uses them.** `managed_paths`, `test_globs`,
  `size_exclude` and `size_budget` are read from the base branch's config when it has one.
- `docs/lifecycle.md` (check table), the config comments and the adversarial-panel skill are
  updated. Known gaps are stated in `docs/security.md`.

## Non-goals

- Migrating existing installs, whose old `test_globs` and missing `managed_paths` stay as they
  are. That belongs to change A (safe adoption), which covers re-running init.sh.
- Converting prose panels (also A).
- Judging whether panel findings are honest. The gate checks structure; the human approver
  checks substance.

## Impact

- `scripts/lib/check_change.py` (about 60 lines), `openspec/config.yaml`, `scripts/init.sh`,
  `tests/`, `docs/lifecycle.md`, `docs/security.md`, `.claude/skills/adversarial-panel/SKILL.md`
  (+ generated `.agents` copy).
