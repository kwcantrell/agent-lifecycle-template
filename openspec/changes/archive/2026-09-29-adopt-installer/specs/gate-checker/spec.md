## MODIFIED Requirements

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
