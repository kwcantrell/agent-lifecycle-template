## ADDED Requirements

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
