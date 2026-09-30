## ADDED Requirements

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
