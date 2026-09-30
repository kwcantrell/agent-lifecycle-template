# YAML parse gate

Tier: 2
Tier reason: touches scripts/lib/check_change.py (high-risk path); adds a gate to every stage.

Approved-by: Kalen 2026-09-29

## Why

From the initial commit until PR #6, `.pre-commit-config.yaml` didn't parse: an unquoted `: ` in a
hook name. pre-commit couldn't load it, so the pre-commit and pre-push gates the docs describe never
ran, and CI, which doesn't parse that file, stayed green. It was found by hand while installing
into autologger-2. A config file that silently fails to load disables whatever it configures.

## What Changes

- **A new `yaml` check parses YAML files.** It covers every tracked `.yml`/`.yaml` file, plus
  untracked non-ignored ones outside CI. It uses `safe_load_all`, so multi-document files are fine,
  and unknown tags like `!Ref` and `!vault` are accepted as plain values. Each file is checked
  on its own: any error, including constructor errors, deep nesting and bad encodings, becomes a
  FAIL naming that file and, where known, the line.
- **`.pre-commit-config.yaml` is checked for shape too.** Top-level `repos` must be a list, each repo
  must have `repo` and a `hooks` list, and each hook must have an `id`. Valid YAML with the wrong
  shape also stops pre-commit loading it.
- **Stage-aware.** The `pr` stage (CI) fails on any broken YAML in the repo, since the motivating
  file was committed in the initial commit and a changed-files-only scan would never recheck it.
  The `commit` and `hook` stages fail on YAML the change touched, and only warn on untouched
  broken files, so a repo that already has broken YAML doesn't deadlock the Stop hook.
- **No exclusion list.** Every YAML file must parse. Repos with Helm templates (`{{ }}`) will fail
  the PR stage; an exclusion mechanism waits for the first real case (ADR 0016).
- docs/lifecycle.md check table, and ADR 0016.

## Non-goals

- JSON, TOML, or schema validation beyond the pre-commit shape.
- Duplicate keys (PyYAML keeps the last). A possible follow-up.
- Exclusions for templated YAML.

## Impact

- `scripts/lib/check_change.py` (about 60 lines), `tests/`, `docs/lifecycle.md`,
  `docs/decisions/0016-config-files-must-parse.md`. No config or installer change: adopt.py's
  `render_lifecycle` needs no new key.
