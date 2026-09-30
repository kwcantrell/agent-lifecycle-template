## ADDED Requirements

### Requirement: YAML changes don't introduce duplicate keys
The yaml gate SHALL find mappings that state the same key twice (keys equal in Python after loading; merge keys exempt; tagged mappings included) and report the key as written with its line. A duplicate the change introduces, beyond those in the same file on the merge-base, SHALL fail the check at every stage. A duplicate already present on the merge-base SHALL only warn.

#### Scenario: Introduced duplicate
- **WHEN** a change adds `permissions: write` to a mapping that already has `permissions: read`
- **THEN** the yaml check fails naming the file, the key and the second line

#### Scenario: Equality and tags
- **WHEN** a new file has a mapping with `1: a` and `1.0: b`, or a `!Sub` mapping with a key twice
- **THEN** the yaml check fails; a mapping with `1: a` and `"1": b` passes

#### Scenario: Merge keys
- **WHEN** a mapping uses `<<: [*a, *b]` and overrides an inherited key
- **THEN** the yaml check passes

#### Scenario: Inherited duplicate
- **WHEN** a file on the base already has a duplicate key and the change edits another line of it
- **THEN** the yaml check warns, at the hook and pr stages, and doesn't fail
