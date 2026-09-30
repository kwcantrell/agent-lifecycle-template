## ADDED Requirements

### Requirement: ADR numbers are unique
The gate checker SHALL find files in `docs/decisions/` named `NNNN-*.md` (extension in any case) that share a number. At the `pr` stage any duplicate SHALL fail the check. At the `commit` and `hook` stages a duplicate SHALL fail it when the change touched one of its files, and SHALL only warn otherwise.

#### Scenario: Duplicate added by the change
- **WHEN** the change adds `0016-b.md` and `0016-a.md` exists
- **THEN** the `adr` check fails in every stage, naming both files

#### Scenario: Pre-existing duplicate
- **WHEN** `0005-a.md` and `0005-b.md` are both on the base and the change touches neither
- **THEN** the `hook` stage warns and the `pr` stage fails

#### Scenario: Renames
- **WHEN** the change renames `0016-a.md` to `0016-b.md`, or renumbers its own new ADR to a free number
- **THEN** the `adr` check passes

#### Scenario: Other naming ignored
- **WHEN** `docs/decisions/` holds `adr-001.md`, `README.md` and `0007-x.MD`
- **THEN** only `0007-x.MD` is considered, and the check passes
