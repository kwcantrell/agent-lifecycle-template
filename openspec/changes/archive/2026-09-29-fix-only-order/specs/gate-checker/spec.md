## ADDED Requirements

### Requirement: Check results do not depend on --only order
The gate checker SHALL resolve the change directory and tier before running any check, so every check's result is the same whatever order `--only` lists the checks in.

#### Scenario: Tier-dependent check listed before change
- **WHEN** `scripts/check-change.sh --only approval,panel,change` runs on a branch with an approved tier 2 change whose panel has no open critical finding
- **THEN** `approval`, `panel` and `change` report PASS, in that order

#### Scenario: Change not requested
- **WHEN** `scripts/check-change.sh --only approval,panel` runs on the same branch
- **THEN** `approval` and `panel` report PASS

### Requirement: A change failure is never hidden
When `change` or a check that depends on it is requested, the gate checker SHALL count a failing `change` result toward the exit code and print it even when `change` is not in `--only`, and SHALL NOT run checks that depend on the change after it fails. Checks that need no change context SHALL be unaffected by a `change` failure.

#### Scenario: Change fails but is not requested
- **WHEN** a branch has two change directories and `scripts/check-change.sh --only approval` runs
- **THEN** it prints `FAIL change`, reports `approval` as blocked, and exits 1

#### Scenario: Unrelated check is unaffected
- **WHEN** a branch has two change directories and `scripts/check-change.sh --only build` runs with a passing build command
- **THEN** it exits 0 and prints no `change` line

#### Scenario: PR body declares a tier with no change
- **WHEN** the PR body says `Tier: 1`, there is no change directory, and the `pr` stage runs
- **THEN** `change` fails, dependent checks are blocked, and nothing raises an exception

### Requirement: --only input is validated
The gate checker SHALL trim and de-duplicate `--only` names, and SHALL exit 2 with the list of valid names for an unknown or empty name.

#### Scenario: Duplicate names
- **WHEN** `--only change,change` runs
- **THEN** `change` prints once

#### Scenario: Unknown name
- **WHEN** `--only bogus` or `--only ""` runs
- **THEN** it exits 2, names the unknown check and lists the valid ones, with no traceback
