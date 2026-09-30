## ADDED Requirements

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
