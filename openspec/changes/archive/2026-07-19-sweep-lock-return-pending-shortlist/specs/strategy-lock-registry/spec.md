## MODIFIED Requirements

### Requirement: Lock from completed validation with optional config pick

The system SHALL only create a lock from a completed validation run for a configuration that **passed** validation (`validation.passed`). The lock MUST reference that run directory. After a sweep, when a lock-candidate shortlist was produced, the user MAY lock a shortlist configuration or another **passing** configuration from that same run; otherwise the user MAY lock the engine-preferred passing configuration or another **passing** configuration from that same run. Lock activation MUST still satisfy `lockable` (empty material reviews or complete human sign-off per strategy-lock-integrity). If the selected configuration lacks a full artifact bundle (including equity/drawdown series) for charting and lock snapshot needs, the system MUST run single-configuration validation for that configuration before activating the lock. After a single-configuration run, the lock applies only if that configuration passed and is `lockable`.

#### Scenario: Lock references run directory

- **WHEN** the user locks a configuration after a successful run
- **THEN** the lock record stores the run directory that contains artifacts for that run

#### Scenario: User locks non-preferred sweep row via single-config

- **WHEN** a sweep run has multiple passing configurations
- **AND** the user selects a passing configuration other than the engine-preferred lock candidate
- **AND** that configuration does not yet have a full artifact bundle in the run
- **THEN** the system runs single-configuration validation for the selected configuration
- **AND** activates a lock only after that validation passes, the configuration is `lockable`, and artifacts exist

#### Scenario: User locks shortlist primary via sign-off

- **WHEN** a sweep produced a lock-candidate shortlist with zero natural `lockable` rows
- **AND** the user selects the shortlist `primary` configuration with complete human sign-off
- **THEN** the configuration becomes the active strategy lock
- **AND** the lock snapshot references that `config_id` and run directory

#### Scenario: Non-passing configuration cannot be locked

- **WHEN** a configuration did not pass validation
- **THEN** the system does not allow it to become the active strategy lock
