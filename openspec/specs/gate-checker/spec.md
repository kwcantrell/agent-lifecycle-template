# gate-checker Specification

## Purpose
Makes the gate checker's results trustworthy for any subset of checks: order never changes a result, and a change failure is never hidden.

## Requirements

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

### Requirement: Panel findings must be machine-readable
The panel gate SHALL treat only top-level checklist items outside code blocks and HTML comments as findings. It SHALL fail when there are no findings and no `No findings.` line, when any finding lacks an exact lowercase `[critical]`, `[major]` or `[minor]` tag, when a `[critical]` is open, or when a ticked `[critical]` or `[major]` lacks `Resolved:` or `Declined`.

#### Scenario: Prose-only panel
- **WHEN** panel.md discusses findings in prose with no checklist items
- **THEN** the panel gate fails, saying no findings are in checklist format

#### Scenario: Clean panel
- **WHEN** panel.md has no checklist items and a line `No findings.`
- **THEN** the panel gate passes

#### Scenario: No findings hidden in a code block
- **WHEN** the only `No findings.` line is inside a fenced code block
- **THEN** the panel gate fails

#### Scenario: Untagged or mis-tagged item
- **WHEN** panel.md has `- [ ] Drops rows` or `- [ ] [Critical] Drops rows`
- **THEN** the panel gate fails, naming the item

#### Scenario: Nested sub-bullet
- **WHEN** a tagged finding has an indented `  - [ ] see above` under it
- **THEN** the sub-bullet is not treated as a finding

#### Scenario: Ticked critical without resolution
- **WHEN** panel.md has `- [x] [critical] Drops rows` with no `Resolved:` or `Declined`
- **THEN** the panel gate fails

### Requirement: Tests are recognized at any depth
The default test globs SHALL match `test/`, `tests/` and `__tests__/` directories at any depth.

#### Scenario: Nested tests folder
- **WHEN** `src/app.sh` and `scripts/tests/test-app.sh` change together
- **THEN** tests-with-code passes

### Requirement: Lifecycle-managed files are not the target's source
The tests-with-code and size gates SHALL ignore changed files matching `lifecycle.managed_paths`. The installer SHALL set that list to the exact files it installs, unless the target already has a value.

#### Scenario: Managed file changed without tests
- **WHEN** the only source change is a managed file such as `scripts/check-change.sh`
- **THEN** tests-with-code passes

#### Scenario: Managed lines don't count toward size
- **WHEN** a managed file changes by more lines than the size budget
- **THEN** the size gate passes

#### Scenario: Installer fills managed_paths
- **WHEN** init.sh installs into a target whose config has no `managed_paths`
- **THEN** the target lists exactly the installed checker, scripts and hooks, and this repo keeps `managed_paths: []`

#### Scenario: Installer keeps a target's value
- **WHEN** the target's config already sets `managed_paths`
- **THEN** init.sh leaves it unchanged

### Requirement: A PR cannot grant its own exemptions
The gate checker SHALL read `managed_paths`, `test_globs`, `size_exclude` and `size_budget` from the base branch's `openspec/config.yaml` when the base has one.

#### Scenario: Same-PR exemption
- **WHEN** a PR adds `src/**` to `managed_paths` and changes `src/app.py` without tests
- **THEN** tests-with-code still fails

### Requirement: In-flight changes that predate the lifecycle can be grandfathered
The gate checker SHALL treat a change as grandfathered only when its id is in the merge-base's `lifecycle.grandfathered_changes` (a list of strings; any other value counts as empty) and `openspec/changes/<id>/` exists on the merge-base. For a grandfathered change it SHALL report WARN for `change`, WARN or PASS for `risk-floor` (listing high-risk paths touched), SKIP for `approval`, `panel`, `tasks`, `evidence`, `artifacts-first` and `size`, and run every other check normally. In CI the PR body SHALL contain `Grandfathered: <id>`.

#### Scenario: Grandfathered change without a Tier line
- **WHEN** a branch changes `openspec/changes/legacy/`, which exists on the merge-base, has no `Tier:` line, and `legacy` is in the merge-base's `grandfathered_changes`
- **THEN** `change` reports WARN, the listed checks report SKIP, and the run exits 0 if the other gates pass

#### Scenario: High-risk paths are shown, not skipped
- **WHEN** that branch also changes `scripts/x.sh`
- **THEN** `risk-floor` reports WARN naming `scripts/x.sh`

#### Scenario: CI needs the PR declaration
- **WHEN** the PR event body lacks `Grandfathered: legacy`
- **THEN** `change` fails

#### Scenario: Archive of a grandfathered change
- **WHEN** the branch moves it to `openspec/changes/archive/2026-10-01-legacy/`
- **THEN** it is still grandfathered

#### Scenario: New change reusing a listed id
- **WHEN** `legacy` is listed but `openspec/changes/legacy/` is not on the merge-base
- **THEN** the change is not grandfathered, and the Tier failure says why

#### Scenario: The PR's own list is ignored
- **WHEN** only the PR's config lists the change, whether or not the base has a lifecycle block
- **THEN** the change is not grandfathered

#### Scenario: Malformed list
- **WHEN** the base's `grandfathered_changes` is missing, null, or the string `legacy`
- **THEN** no change is grandfathered, and nothing raises

### Requirement: Tier 0 carries no change
The gate checker SHALL fail a change directory whose proposal, or whose PR body, declares tier 0.

#### Scenario: Tier 0 change directory
- **WHEN** a branch adds `openspec/changes/x/proposal.md` with `Tier: 0`
- **THEN** `change` fails, saying tier 0 needs no OpenSpec change
