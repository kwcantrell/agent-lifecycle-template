## ADDED Requirements

### Requirement: The installer never modifies existing files
The installer SHALL create only paths that do not exist on the filesystem (including ignored files and symlinks), SHALL NOT write where a parent's real path is outside the target, SHALL NOT run the target's own scripts or `openspec init` on a repo that already has OpenSpec-generated files, and SHALL record each created path in `.lifecycle-adoption/MANIFEST` after creating it.

#### Scenario: Existing and ignored files untouched
- **WHEN** the target has AGENTS.md, a gitignored `.claude/settings.json`, `openspec/config.yaml` and its own `.agents/skills/mine/`
- **THEN** after init.sh their bytes are unchanged and `.agents/skills/mine/` still exists

#### Scenario: Symlink outside the repo
- **WHEN** `docs` is a symlink to a directory outside the target, including a sibling whose path shares the target's prefix
- **THEN** nothing is written there, and the path is reported as skipped

#### Scenario: Existing adoption folder
- **WHEN** `.lifecycle-adoption/` already exists
- **THEN** init.sh exits 1 and writes nothing

#### Scenario: Adoption folder ignored
- **WHEN** an install has written `.lifecycle-adoption/`
- **THEN** `git status --porcelain` in the target lists nothing under it

### Requirement: Undo removes exactly what was created
`adopt.py undo` SHALL validate every MANIFEST line before removing anything, and SHALL remove listed files and then listed directories only when empty.

#### Scenario: Undo restores the tree
- **WHEN** undo runs after an install on a repo with no `openspec/`
- **THEN** `git status --porcelain --ignored` matches what it was before, and no directory the install created remains

#### Scenario: Tampered manifest
- **WHEN** MANIFEST contains `..`, `/etc`, `.git` or a path outside the target
- **THEN** undo exits 1 and removes nothing

#### Scenario: User file added later
- **WHEN** a user adds a file inside a directory the install created, then runs undo
- **THEN** that file and its directory remain

### Requirement: Conflicts produce proposals and a risk report
For each existing AGENTS.md, CLAUDE.md, `.claude/settings.json` or `openspec/config.yaml`, the installer SHALL write a proposal into `.lifecycle-adoption/` with a README checklist for a human, and SHALL report target settings that weaken the lifecycle.

#### Scenario: Proposed settings
- **WHEN** the target's settings.json has its own allow list and `enabledPlugins`
- **THEN** the proposed settings.json keeps both, adds the template deny rules and `sandbox.enabled: true`, and adds each hook once whose script was installed identical to the template

#### Scenario: Hooks already referenced
- **WHEN** a target hook command is `"$CLAUDE_PROJECT_DIR"/.claude/hooks/stop-check.sh`
- **THEN** the proposal doesn't add a second Stop hook

#### Scenario: Differing hook script
- **WHEN** the target already has `.claude/hooks/stop-check.sh` with different content
- **THEN** it is not overwritten, the proposal doesn't wire it, and the risk report says so

#### Scenario: Risky settings reported
- **WHEN** the target sets `defaultMode: bypassPermissions` or allows bare `Bash`
- **THEN** the terminal summary and README list them under risks

#### Scenario: Unwired hooks stated
- **WHEN** settings.json existed
- **THEN** the first "Next steps" item says the hooks are not active until the proposed settings.json is merged

#### Scenario: Unmergeable settings
- **WHEN** the target's settings.json contains a comment
- **THEN** no proposed settings.json is written, the README says why, and init.sh exits 0

#### Scenario: Config snippet
- **WHEN** the target config has `rules` but no `lifecycle`
- **THEN** the snippet contains a `lifecycle` section and no `rules` section, and the target config is unchanged

#### Scenario: Existing lifecycle block
- **WHEN** the target config has a `lifecycle` block without `managed_paths`
- **THEN** the README lists `managed_paths` as missing

#### Scenario: Guide blocks
- **WHEN** the target has AGENTS.md and CLAUDE.md
- **THEN** the AGENTS block is at most 12 lines and states that the lifecycle gates win on conflict, and the CLAUDE block imports `@docs/agent-lifecycle.md`

### Requirement: Fresh repos are set up without proposals
When the target has no `openspec/` and no OpenSpec-generated files, the installer SHALL write the template config with target values as a new file, then run `openspec init`, recording its new files in MANIFEST.

#### Scenario: Fresh install
- **WHEN** init.sh runs on a repo with no agent or OpenSpec files
- **THEN** the config has the lifecycle block with the given commands and `managed_paths` including `scripts/lib/adopt.py`, and `.lifecycle-adoption/` holds only MANIFEST, README and .gitignore
