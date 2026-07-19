## ADDED Requirements

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
