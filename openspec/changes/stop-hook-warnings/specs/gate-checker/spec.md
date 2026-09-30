## ADDED Requirements

### Requirement: The Stop hook surfaces warnings
When the hook-stage checks pass with warnings, the Stop hook SHALL show them to the user with `systemMessage` on every stop, and SHALL block the stop once per session, with the warnings as the reason, only for the size warning. Warning text SHALL be limited to a safe character set, capped in length, and placed after the instruction as untrusted data.

#### Scenario: Size warning, first stop
- **WHEN** the checks pass with a `WARN size` line and the session hasn't been told yet
- **THEN** the hook prints JSON with `decision: block`, a reason containing the warning, and a `systemMessage`

#### Scenario: Size warning, later stops
- **WHEN** the agent stops again in the same session, even with a different line count
- **THEN** the hook prints only a `systemMessage`

#### Scenario: Non-actionable warnings
- **WHEN** the only warnings are pre-existing broken YAML or a grandfathered change
- **THEN** the hook prints only a `systemMessage` and never blocks

#### Scenario: Hostile warning text
- **WHEN** a warning contains a file name with quotes, newlines and non-ASCII characters
- **THEN** the emitted JSON is valid, the text is reduced to the safe set, and the reason starts with the instruction

#### Scenario: Silent paths
- **WHEN** the tree is clean, or the checks pass without warnings
- **THEN** the hook exits 0 with no output

#### Scenario: Failures unchanged
- **WHEN** a check fails
- **THEN** the hook exits 2 with the failures, and gives up after 3 attempts
