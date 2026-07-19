# run-artifacts

## Purpose

Define run artifact persistence, schema versioning, and machine-readable outputs for validation and sweep runs.

## Requirements

### Requirement: Stable intermediate artifact bundle

Each full validation run SHALL emit a stable intermediate artifact bundle under the run output directory. The bundle MUST be suitable for later ledger ingestion and GUI consumption without requiring a rewrite of the core engine. Human-facing CSV and markdown reports remain primary Phase 1 outputs; the artifact bundle is additive.

#### Scenario: Bundle emitted after successful run

- **WHEN** a validation sweep completes successfully
- **THEN** an artifacts subdirectory (or equivalent bundle path) exists under the output directory
- **AND** the bundle contains machine-readable files for configuration snapshot, events, metrics summary, and suitability summary






### Requirement: Configuration snapshot artifact

The artifact bundle MUST include a configuration snapshot for the locked configuration (and MAY include all sweep configurations). The snapshot MUST capture allocation weights, stock sub-split, bond variant, DCA method, rebalancing threshold, enablement flags relevant to execution, and effective investor profile thresholds.

#### Scenario: Locked config snapshot fields

- **WHEN** a configuration is locked
- **THEN** the configuration snapshot includes stock sub-split and effective profile thresholds
- **AND** field names remain stable across runs with the same schema version






### Requirement: Simulation event artifact

The artifact bundle MUST include a chronologically ordered event log for the locked configuration covering contribution, purchase, sale, rebalance, pending-cash, and withdrawal/lifecycle cashflow events used by the validation path. Each event MUST include date, event type, symbol when applicable, cash amount, and quantity or weight fields needed to reconstruct holdings without re-running pricing when prices are also exported or otherwise available.

#### Scenario: Event log reconstructs trade flow

- **WHEN** the locked configuration simulation completes
- **THEN** the event artifact lists base-position, DCA, and rebalance events in chronological order
- **AND** QDII pending-cash related events are included when quota constraints bind






### Requirement: Metrics and suitability artifacts

The artifact bundle MUST include a metrics summary and a suitability summary for the locked configuration. The suitability summary MUST list each investor profile, classification, reasons, and effective thresholds used.

#### Scenario: Suitability artifact matches lock document

- **WHEN** strategy-lock.md is generated
- **THEN** the suitability artifact classifications match the Investor Profile Suitability section
- **AND** reasons are present for each profile






### Requirement: Artifact schema version

Every artifact file MUST declare a schema_version field (or equivalent metadata) so later ledger/GUI consumers can detect incompatible format changes.

#### Scenario: Schema version present

- **WHEN** any intermediate artifact file is written
- **THEN** it includes schema_version
- **AND** the initial schema_version for this change is documented as `1`






### Requirement: JSON as machine-readable artifact format

Intermediate artifacts MUST be emitted in JSON (one or more `.json` files). CSV and markdown remain the human-facing Phase 1 reports and MUST NOT be removed by this change.

#### Scenario: JSON artifacts coexist with CSV and markdown

- **WHEN** a validation run completes
- **THEN** JSON intermediate artifacts are present
- **AND** sweep_results.csv and strategy-lock.md are still produced

### Requirement: Equity and drawdown series artifact

The artifact bundle for a successfully evaluated or locked configuration MUST include a machine-readable equity/NAV series derived from the simulation daily portfolio values, plus a drawdown series computed from that equity path. The file MUST declare `schema_version` and include dated points sufficient for the workbench to render charts without re-running simulation.

#### Scenario: Equity curve artifact present

- **WHEN** a locked or single-configuration validation completes successfully
- **THEN** an equity-curve artifact (e.g. `artifacts/equity_curve.json`) exists under the run output directory
- **AND** it includes schema_version, dates, equity/NAV levels, and drawdown values aligned to those dates

### Requirement: Stress summary artifact for tabular UI

When stress-test results are available for the evaluated configuration, the artifact bundle MUST include a compact stress-summary JSON listing scenario identifiers, key reported metrics, and pass/review/fail (or equivalent) classifications suitable for a table or traffic-light display. Full scenario path series are not required for v1 charts.

#### Scenario: Stress summary lists classifications

- **WHEN** validation produces stress results for the configuration
- **THEN** a stress-summary artifact is written
- **AND** each listed scenario includes an identifier and a classification usable by the UI

### Requirement: Lock integrity fields in artifacts

The artifact bundle and strategy-lock markdown MUST record `validation.passed`, `lockable`, material `needs_review` items, optional human sign-off (reviewer, timestamp, rationale, acknowledged items), CPI assumption used for historical real metrics, and stress mechanism labels where applicable.

#### Scenario: Bundle exposes lockable and sign-off

- **WHEN** a configuration is promoted to active lock with human sign-off
- **THEN** the artifact bundle includes `lockable: true` and the sign-off payload
- **AND** strategy-lock.md includes matching Sign-off and Assumptions sections

#### Scenario: Soft-pass without lock omits active lock stamp

- **WHEN** a configuration is `validation.passed` but not `lockable`
- **THEN** artifacts may still store the validation result for inspection
- **AND** MUST NOT mark the configuration as the active strategy lock

### Requirement: Lock shortlist artifact

When the lock-candidate shortlist path runs after a sweep, the run output directory MUST include a machine-readable shortlist artifact (JSON with `schema_version`) and a human-readable markdown companion summarizing each role’s `config_id`, key metrics, material review differential, and pros/cons. These artifacts are additive and MUST NOT replace `sweep_results.csv`.

#### Scenario: Shortlist files written without active lock

- **WHEN** a sweep completes with zero natural `lockable` configurations and builds a shortlist
- **THEN** `lock-shortlist.json` (or equivalent) and `lock-shortlist.md` exist under the output directory
- **AND** each listed candidate includes `lockable: false` until a later sign-off lock
- **AND** `sweep_results.csv` remains present

