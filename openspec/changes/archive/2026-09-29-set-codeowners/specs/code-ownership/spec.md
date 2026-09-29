## ADDED Requirements

### Requirement: Lifecycle paths have a resolvable human owner
The repository SHALL name a real GitHub user or team as code owner for every lifecycle guardrail path (AGENTS.md, CLAUDE.md, .claude/, .agents/, .github/, scripts/, openspec/config.yaml, openspec/changes/, docs/decisions/).

#### Scenario: Placeholder removed
- **WHEN** `.github/CODEOWNERS` is read in this repository
- **THEN** it contains no `@OWNER` placeholder and names `@kwcantrell` for each lifecycle path

### Requirement: Installer renders CODEOWNERS for the target
The installer SHALL generate the target's CODEOWNERS from a template with a validated owner supplied at install time, SHALL NOT copy this repository's own owners into a target, and SHALL NOT write or modify CODEOWNERS when the target already has one.

#### Scenario: Owner supplied
- **WHEN** `scripts/init.sh --owner @acme/maintainers TARGET` runs on a repo without CODEOWNERS
- **THEN** `TARGET/.github/CODEOWNERS` names `@acme/maintainers` for each lifecycle path and does not mention `@kwcantrell` or `@OWNER`

#### Scenario: No owner supplied
- **WHEN** init.sh runs non-interactively without `--owner`
- **THEN** it writes no CODEOWNERS file and the warning appears under "Next steps"

#### Scenario: Invalid owner rejected
- **WHEN** `--owner` is not a single-line `@user`, `@org/team` or email (for example `acme`, `@a#b`, or a value containing a newline)
- **THEN** init.sh exits non-zero before writing any file

#### Scenario: Existing CODEOWNERS kept
- **WHEN** the target already has CODEOWNERS in `.github/`, the repo root or `docs/`
- **THEN** init.sh leaves it unchanged, writes no other CODEOWNERS, lists it under skipped, and prints the lifecycle paths to add by hand

#### Scenario: Dry run reports the outcome
- **WHEN** init.sh runs with `--dry-run`
- **THEN** it prints what it would do with CODEOWNERS and writes nothing
