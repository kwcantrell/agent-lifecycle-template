## MODIFIED Requirements

### Requirement: Changed paths are read exactly
The gate checker SHALL read each path it takes from git whole, whatever characters it contains. The
changed-file list SHALL include both sides of a rename: the old path as deleted and the new path as
added. The first-commit list that artifacts-first reads SHALL be read the same way. The size gate
SHALL take every line count from git, SHALL detect renames regardless of `diff.renames`, and SHALL
count a moved file by where it lands:
- between two counted paths: its content delta;
- from an excluded path to a counted one: the whole file;
- from a counted path to an excluded one: the old file's lines;
- between two excluded paths: nothing.

#### Scenario: Path with a space
- **WHEN** a branch adds `docs/a b.md`
- **THEN** the changed paths contain `docs/a b.md`, and neither `docs/a` nor `b.md`

#### Scenario: Rename out of a directory
- **WHEN** a branch moves `scripts/x.sh` to `x.sh`
- **THEN** the changed paths contain both `scripts/x.sh` and `x.sh`, and `risk-floor` sees `scripts/x.sh`

#### Scenario: Plan commit with a space or non-ASCII name
- **WHEN** a tier 2 branch's first commit holds only `openspec/changes/<id>/` files, one named `a b.md` and one `é.md`
- **THEN** artifacts-first passes

#### Scenario: Stray file in the plan commit
- **WHEN** a tier 2 branch's first commit also holds `src/a b.py`, alongside an `openspec/changes/archive/` file
- **THEN** artifacts-first fails and names `src/a b.py`

#### Scenario: Pure move inside counted source
- **WHEN** a branch moves an 8-line `lib/a.py` to `lib/b.py` unchanged, with a size budget of 10
- **THEN** the size gate counts 0 lines for it and passes

#### Scenario: Move with edits inside counted source
- **WHEN** a branch moves a 20-line `lib/a.py` to `lib/b.py` and adds 3 lines
- **THEN** the size gate counts 3 lines for it

#### Scenario: Move from an excluded folder into counted source
- **WHEN** a branch moves a 50-line `tests/big.py` to `src/big.py` and adds one line, with a size budget of 10
- **THEN** the size gate counts 51 lines and fails

#### Scenario: Move from counted source into an excluded folder
- **WHEN** a branch moves a 50-line `lib/a.py` to `tests/a.py` unchanged, with a size budget of 10
- **THEN** the size gate counts 50 lines and fails

#### Scenario: Rename detection ignores diff.renames
- **WHEN** `diff.renames` is `false` and a branch moves an 8-line `lib/a.py` to `lib/b.py` unchanged, with a size budget of 10
- **THEN** the size gate passes

#### Scenario: Binary move followed by other changes
- **WHEN** a branch moves a binary `lib/b.bin` to `lib/c.bin` and adds 3 lines to `lib/x.py`
- **THEN** the size gate counts 3 lines

#### Scenario: A file git counts as text, moved into an exclusion
- **WHEN** `.gitattributes` has `*.dat diff`, a branch moves a 30-line `lib/n.dat` containing a NUL byte to `tests/n.dat`, and adds 3 lines to `lib/x.py`, with a size budget of 100
- **THEN** the size gate counts 33 lines, never less than the 3 lines added elsewhere

#### Scenario: Non-ASCII path matches its exclusion
- **WHEN** a branch adds 50 lines to `docs/é.md`, `docs/**` is excluded, and the size budget is 10
- **THEN** the size gate passes

#### Scenario: Nothing changed
- **WHEN** a branch has no changes against its base, and a size budget is set
- **THEN** the size gate passes with 0 lines
