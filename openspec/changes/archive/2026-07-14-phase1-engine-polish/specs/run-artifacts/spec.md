## ADDED Requirements

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
