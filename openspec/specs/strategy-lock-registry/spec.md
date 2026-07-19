# strategy-lock-registry

## Purpose

Define the immutable local strategy-lock registry that stores append-only lock history and self-contained active-lock snapshots for the personal workbench.

## Requirements

### Requirement: Immutable strategy lock history

The system SHALL persist strategy locks in a local SQLite store. Creating a new active lock MUST retain all previous locks (append-only history) and MUST clear the active flag on the previously active lock rather than deleting it.

#### Scenario: Relock archives previous active lock

- **WHEN** an active lock exists for configuration A
- **AND** the user activates a new lock for configuration B
- **THEN** configuration B is the sole active lock
- **AND** configuration A remains stored with inactive status
- **AND** no lock row is deleted

### Requirement: Self-contained active lock snapshot

Each lock record MUST store at least: lock timestamp, `config_id`, path to the originating run directory, intended profile id when applicable, and a JSON snapshot that is sufficient to reconstruct live targets without consulting mutable code defaults. The snapshot MUST include allocation weights, bond variant, DCA method, rebalance threshold, stock sub-split, **resolved instrument symbols and target weights**, and a metrics/suitability summary for display. Exactly one lock MAY be active at a time; zero active locks is allowed before the first lock.

#### Scenario: Active lock readable without re-run

- **WHEN** the user opens the workbench with an active lock
- **THEN** the UI can display the locked `config_id`, target quadrant weights, and instrument targets from the stored snapshot
- **AND** does not require re-executing validation to show that snapshot

#### Scenario: Targets survive missing run directory

- **WHEN** an active lock’s run directory has been deleted
- **THEN** the workbench can still display target weights from the lock snapshot
- **AND** artifact-dependent detail views may report that run files are missing

### Requirement: Lock from completed validation with optional config pick

The system SHALL only create a lock from a completed validation run for a configuration that **passed** validation (`validation.passed`). The lock MUST reference that run directory. After a sweep, the user MAY lock the engine-preferred passing configuration or another **passing** configuration from that same run. If the selected configuration lacks a full artifact bundle (including equity/drawdown series) for charting and lock snapshot needs, the system MUST run single-configuration validation for that configuration before activating the lock. After a single-configuration run, the lock applies only if that configuration passed.

#### Scenario: Lock references run directory

- **WHEN** the user locks a configuration after a successful run
- **THEN** the lock record stores the run directory that contains artifacts for that run

#### Scenario: User locks non-preferred sweep row via single-config

- **WHEN** a sweep run has multiple passing configurations
- **AND** the user selects a passing configuration other than the engine-preferred lock candidate
- **AND** that configuration does not yet have a full artifact bundle in the run
- **THEN** the system runs single-configuration validation for the selected configuration
- **AND** activates a lock only after that validation passes and artifacts exist

#### Scenario: Non-passing configuration cannot be locked

- **WHEN** a configuration did not pass validation
- **THEN** the system does not allow it to become the active strategy lock
