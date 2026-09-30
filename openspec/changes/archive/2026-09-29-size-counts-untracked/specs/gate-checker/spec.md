## ADDED Requirements

### Requirement: The size gate counts untracked files locally
Outside CI, the size gate SHALL count untracked, non-ignored files as added lines, with the same exclusions as tracked changes and git's line and binary rules. In CI it SHALL count committed diffs only.

#### Scenario: New file before commit
- **WHEN** a 401-line untracked source file exists and nothing is committed, at the `pr` stage
- **THEN** the size gate fails

#### Scenario: Excluded, ignored and binary files
- **WHEN** the untracked files are a 500-line test file, a gitignored 500-line file and a binary file
- **THEN** the size gate passes

#### Scenario: Names with spaces and non-ASCII
- **WHEN** a 401-line untracked file is named `é new.py`
- **THEN** the size gate counts it and fails at the `pr` stage

#### Scenario: Git line rules
- **WHEN** an untracked file has no trailing newline
- **THEN** its last line is counted, as git counts it

#### Scenario: CI ignores untracked files
- **WHEN** `CI` is set and a 500-line untracked file exists
- **THEN** it is not counted

### Requirement: The hook stage warns on size
At the `hook` stage the size gate SHALL report WARN instead of FAIL when over budget, and the `pr` stage SHALL still fail.

#### Scenario: Stop hook sees it without blocking
- **WHEN** `scripts/check-change.sh --stage hook` runs with an over-budget untracked file
- **THEN** it reports `WARN size` and exits 0 if the other gates pass
