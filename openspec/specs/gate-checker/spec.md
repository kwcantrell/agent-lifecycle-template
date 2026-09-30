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
The tests-with-code and size gates SHALL ignore changed files matching `lifecycle.managed_paths`. The installer SHALL write that list, the exact files it installs including `scripts/lib/adopt.py`, into a config it creates, and SHALL include it in the proposal when the target already has a config.

#### Scenario: Managed file changed without tests
- **WHEN** the only source change is a managed file such as `scripts/check-change.sh`
- **THEN** tests-with-code passes

#### Scenario: Managed lines don't count toward size
- **WHEN** a managed file changes by more lines than the size budget
- **THEN** the size gate passes

#### Scenario: Installer fills managed_paths
- **WHEN** init.sh installs into a target with no config
- **THEN** the new config lists exactly the installed checker, scripts, adopt.py and hooks, and this repo keeps `managed_paths: []`

#### Scenario: Installer keeps a target's value
- **WHEN** the target already has a config
- **THEN** init.sh leaves it unchanged, and the proposal lists the lifecycle keys it lacks

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

### Requirement: Changed paths are read exactly
The gate checker SHALL read each changed path whole, whatever characters it contains, and SHALL
list both sides of a rename: the old path as deleted and the new path as added.

#### Scenario: Path with a space
- **WHEN** a branch adds `docs/a b.md`
- **THEN** the changed paths contain `docs/a b.md`, and neither `docs/a` nor `b.md`

#### Scenario: Rename out of a directory
- **WHEN** a branch moves `scripts/x.sh` to `x.sh`
- **THEN** the changed paths contain both `scripts/x.sh` and `x.sh`, and `risk-floor` sees `scripts/x.sh`

### Requirement: Task-list edits to existing archives are not a change
When the gate checker resolves a branch's change, it SHALL NOT count a directory
`openspec/changes/archive/<name>/` when all of these hold:
- `<name>` matches `YYYY-MM-DD-<id>`, where `<id>` uses only lowercase letters, digits and hyphens;
- the directory exists on the merge-base;
- its only difference from the merge-base, across committed, staged, unstaged and untracked changes,
  is an in-place modification of `<name>/tasks.md`, which is a regular file on both sides.

It SHALL count every other changed change directory as before. Every `change` result (PASS, WARN or
FAIL) SHALL name each archive it did not count.

#### Scenario: Ticking tasks in several existing archives
- **WHEN** a branch modifies only `tasks.md` in two archives that exist on the merge-base
- **THEN** `change` passes at tier 0 and its message names both archives

#### Scenario: Alongside the branch's own change
- **WHEN** a branch adds `openspec/changes/add-thing/` and modifies only `tasks.md` in an existing archive
- **THEN** `add-thing` is the branch's change, its tier and gates apply, and the message names the archive

#### Scenario: One exempt archive and one counted archive
- **WHEN** a branch modifies only `tasks.md` in archive A, and modifies `proposal.md` in archive B
- **THEN** only B is counted, and the message names A

#### Scenario: The note survives a failure
- **WHEN** a branch modifies only `tasks.md` in an existing archive and adds two change directories
- **THEN** `change` fails "one change per branch" and the message still names the archive

#### Scenario: Another file in the archive
- **WHEN** a branch modifies `tasks.md` and `proposal.md` in an archive that exists on the merge-base
- **THEN** that archive is counted, as before

#### Scenario: A file moved out of the archive
- **WHEN** a branch modifies `tasks.md` in an existing archive and moves that archive's `proposal.md` elsewhere
- **THEN** that archive is counted

#### Scenario: tasks.md added, deleted, moved, or no longer a regular file
- **WHEN** a branch adds, deletes, moves, or replaces with a symlink the `tasks.md` of an archive that exists on the merge-base
- **THEN** that archive is counted

#### Scenario: A file whose name hides behind tasks.md
- **WHEN** a branch modifies `tasks.md` in an existing archive and adds `tasks.md x.txt` beside it
- **THEN** that archive is counted

#### Scenario: A name outside the archive form
- **WHEN** an archive directory's name does not match `YYYY-MM-DD-<id>`
- **THEN** it is never exempt

#### Scenario: The branch archives its own change
- **WHEN** a branch creates `openspec/changes/archive/2026-10-01-add-thing/`, which the merge-base lacks
- **THEN** it is counted, as before

#### Scenario: Archive of a grandfathered id
- **WHEN** `legacy` is grandfathered and a branch modifies only `tasks.md` in the existing `openspec/changes/archive/2026-01-01-legacy/`
- **THEN** it is exempt like any other archive: `change` passes at tier 0 without a `Grandfathered:` line

#### Scenario: A PR declares a tier with only exempt edits
- **WHEN** the PR body says `Tier: 1` and the branch's only change-dir edits are exempt
- **THEN** `change` fails, saying tier 1 needs an OpenSpec change

#### Scenario: No base
- **WHEN** there is no merge-base
- **THEN** no archive is exempt

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

### Requirement: YAML files must parse
The gate checker SHALL parse every tracked `.yml`/`.yaml` file, plus untracked non-ignored ones outside CI, accepting multi-document files and unknown tags, and SHALL report each failing file with its line where known. At the `pr` stage any failing file SHALL fail the check. At the `commit` and `hook` stages a failing file the change touched SHALL fail it, and a failing untouched file SHALL only warn.

#### Scenario: Broken config
- **WHEN** a changed `.pre-commit-config.yaml` contains `name: gates (hook stage: tests)` unquoted
- **THEN** the `yaml` check fails naming the file and line

#### Scenario: Tags and multiple documents
- **WHEN** a file uses `!Ref` tags and `---` document separators
- **THEN** the `yaml` check passes

#### Scenario: Constructor and nesting errors
- **WHEN** a file contains `!!int abc`, or is nested 100,000 levels deep
- **THEN** the check fails naming that file, and the checker doesn't crash

#### Scenario: Pre-existing broken file
- **WHEN** a broken YAML file is committed on the base and the change doesn't touch it
- **THEN** the `hook` stage warns and the `pr` stage fails

#### Scenario: Symlinks skipped
- **WHEN** a tracked `link.yml` is a dangling symlink
- **THEN** the check doesn't fail on it

### Requirement: The pre-commit config has a loadable shape
The gate checker SHALL fail when `.pre-commit-config.yaml` parses but lacks a `repos` list, a repo lacks `repo` or a `hooks` list, or a hook lacks an `id`.

#### Scenario: Wrong shape
- **WHEN** `.pre-commit-config.yaml` is `repos: {}`
- **THEN** the `yaml` check fails naming the file
