# YAML duplicate keys fail

Tier: 2
Tier reason: touches scripts/lib/check_change.py (high-risk path); tightens the yaml gate.

Approved-by: Kalen 2026-09-29

## Why

The yaml gate (ADR 0017) parses every YAML file, but PyYAML silently keeps the last of two
duplicate keys: `a: 1` then `a: 2` loads as `{a: 2}`. In a config, a duplicated key usually means
one setting silently overrides another, like two `permissions:` blocks in a workflow or two `id`s
in a pre-commit hook. That's the same class of silent misconfiguration the gate exists to catch.
ADR 0017 recorded it as a follow-up.

## What Changes

- **The yaml gate finds duplicate keys.** It reports every mapping that states the same key twice,
  at any depth and in tagged mappings (`!Sub`) too, with the key as written and its line.
- **Keys compare as Python compares their loaded values.** `yes`/`true`, `1`/`1.0`/`true` and
  `null`/`~` collide, as they do when PyYAML builds the dict. `1` and `"1"` don't.
- **Merge keys are exempt.** A key inherited through `<<` and then overridden, or several `<<`
  keys, isn't a duplicate.
- **Only introduced duplicates fail.** For each file, the duplicates are compared with the same
  file on the merge-base. A duplicate the change introduces FAILs at every stage. One that was
  already there only WARNs at every stage. So adopted repos aren't blocked on files they never
  edited, and a one-line edit to a file with an old duplicate doesn't block the commit. Unparseable
  YAML keeps the gate's existing rules.
- docs/lifecycle.md yaml row, and an ADR 0017 amendment.

## Non-goals

- Duplicate detection in JSON or other formats.

## Impact

- `scripts/lib/check_change.py` (about 45 lines), `tests/`, `docs/lifecycle.md`,
  `docs/decisions/0017-config-files-must-parse.md`.
