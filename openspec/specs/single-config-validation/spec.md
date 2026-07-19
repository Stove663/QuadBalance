# single-config-validation

## Purpose

Define a programmatic entrypoint that validates exactly one strategy configuration with the same deep validation, reporting, and artifact contract as the sweep lock path.

## Requirements

### Requirement: Single-configuration validation entrypoint

The engine SHALL expose a programmatic entrypoint that validates exactly one `StrategyConfig` (with the same profile and threshold options supported by the sweep path) without enumerating the full sweep space. The entrypoint MUST perform the deep validation and reporting needed to produce lock-document inputs and run artifacts for that configuration.

#### Scenario: One config does not scan full space

- **WHEN** the single-configuration entrypoint is invoked with one strategy configuration
- **THEN** the engine does not evaluate the full combinatorial sweep space
- **AND** it produces validation results for that configuration

### Requirement: Artifact contract parity

A successful single-configuration run MUST write an artifacts bundle under the run output directory with the same schema_versioned JSON files required by `run-artifacts` (configuration snapshot, events, metrics summary, suitability summary, and equity/drawdown series). Human-facing markdown/CSV outputs for the locked or evaluated configuration MUST remain available where applicable.

#### Scenario: Artifacts present after single-config run

- **WHEN** a single-configuration validation completes successfully
- **THEN** `artifacts/config.json`, `artifacts/events.json`, `artifacts/metrics.json`, `artifacts/suitability.json`, and `artifacts/equity_curve.json` (or equivalent equity/drawdown artifact) exist under the output directory
- **AND** each includes schema_version consistent with the run-artifacts capability

### Requirement: Shared truth with sweep lock path

Single-configuration validation MUST reuse the same core simulation, metrics, suitability, and artifact-writing logic used when a sweep locks a configuration, so UI试跑 and sweep-lock results do not diverge in meaning for the same inputs.

#### Scenario: Same config same artifact fields

- **WHEN** the same configuration and profile options are validated via the single-configuration path
- **THEN** emitted metric and suitability fields follow the same schemas as a sweep-produced artifact bundle for that configuration
