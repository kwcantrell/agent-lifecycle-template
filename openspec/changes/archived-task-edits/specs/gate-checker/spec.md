## ADDED Requirements

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
