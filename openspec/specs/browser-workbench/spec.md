# browser-workbench

## Purpose

Define the local NiceGUI personal browser workbench for configuring strategy parameters, running validation, viewing results, managing strategy locks, and accessing ledger and rebalance guidance.

## Requirements

### Requirement: Local NiceGUI workbench entry

The system SHALL provide a localhost NiceGUI application entrypoint that a single personal user can start without authentication. The workbench MUST expose flows to configure investor profile and strategy parameters, start validation runs, view results, manage the active strategy lock, and access ledger and rebalance guidance views.

#### Scenario: Start workbench without CLI validation flags

- **WHEN** the user starts the NiceGUI entrypoint
- **THEN** a browser UI is available on localhost
- **AND** the user can initiate a validation run from the UI without invoking the `quadbalance` CLI

### Requirement: Configure profile and strategy parameters

The workbench SHALL allow selecting an intended investor profile and the mechanical strategy parameters used by the engine (allocation template, bond variant, DCA method, rebalance threshold, stock sub-split, and optional profile threshold overrides). Submitted values MUST map to the same configuration concepts the CLI and engine already use.

#### Scenario: Intended profile drives lock priority context

- **WHEN** the user selects an intended profile and starts a full sweep from the UI
- **THEN** the run uses that profile as the preferred lock-priority context equivalent to `--intended-profile`

### Requirement: Per-run output directories

Each workbench-triggered validation run (full sweep or single-configuration) MUST write outputs under a distinct `output/<run_id>/` directory and MUST NOT overwrite a previous workbench run’s directory in place.

#### Scenario: Second run keeps first run files

- **WHEN** the user completes run A under `output/<run_id_a>/`
- **AND** then starts run B from the workbench
- **THEN** run B writes to a different `output/<run_id_b>/`
- **AND** run A’s files remain intact

### Requirement: Full sweep and single-config run actions

The workbench SHALL offer both a full parameter sweep and a single-configuration validation action. While a run is in progress, the UI MUST show progress or log output and MUST prevent starting a second concurrent run until the current run finishes or fails. Cancel-in-flight is not required in v1.

#### Scenario: Concurrent run blocked

- **WHEN** a validation run is already in progress
- **AND** the user attempts to start another run
- **THEN** the UI does not start a second engine run
- **AND** the user is informed that a run is already active

### Requirement: Results from artifacts and reports

After a successful run, the workbench SHALL present results using the run’s machine-readable artifacts and existing human-facing reports (metrics, suitability, lock document content, and sweep table when applicable) without requiring the user to open files manually. When a sweep completes with zero passing configurations, the UI MUST show that outcome explicitly.

#### Scenario: Artifacts drive metrics panel

- **WHEN** a run completes with an artifacts directory
- **THEN** the UI shows core metrics and suitability classifications consistent with that run’s `metrics.json` and `suitability.json`

#### Scenario: No passing configuration shown

- **WHEN** a full sweep completes with no configuration passing validation
- **THEN** the UI states that no configuration passed
- **AND** still exposes the sweep results table when available

### Requirement: Backtest NAV and drawdown charts

For a successfully evaluated configuration with an equity-curve artifact, the workbench MUST display a backtest NAV/equity trend chart and a drawdown trend chart. Charts MUST be rendered from the artifact series and MUST NOT re-run the portfolio simulation solely to obtain chart data.

#### Scenario: Charts from equity_curve artifact

- **WHEN** the user opens results for a run that includes `artifacts/equity_curve.json`
- **THEN** the UI shows an NAV/equity chart and a drawdown chart
- **AND** the plotted series match the artifact dates and values

### Requirement: Stress results as table or traffic lights

Stress-test outcomes in the workbench MUST be presented primarily as a table and/or traffic-light style summary (scenario, key metrics, classification). Multi-line stress NAV trend charts are not required in v1.

#### Scenario: Stress table visible

- **WHEN** a run includes stress results or a stress-summary artifact
- **THEN** the UI shows a tabular or traffic-light stress summary
- **AND** does not require a multi-scenario NAV trend chart to satisfy this requirement

### Requirement: Lock selection in the UI

After a run, the workbench SHALL allow activating a strategy lock only for configurations that passed validation. The user MAY lock the engine-preferred passing candidate when present, or another passing configuration from that run. If the selected passing configuration lacks a full artifact bundle, the UI MUST trigger single-configuration validation before lock activation. Backtest charts and metrics MUST be labeled as using illustrative engine default capital/contribution assumptions in v1.

#### Scenario: Lock preferred or alternate passing only

- **WHEN** a sweep finishes with a preferred candidate and other passing rows
- **THEN** the user can lock the preferred candidate
- **OR** lock another passing configuration from that run after ensuring artifacts exist (via single-config if needed)

#### Scenario: Illustrative backtest disclaimer shown

- **WHEN** the user views backtest NAV or drawdown charts
- **THEN** the UI discloses that path results use engine default capital and contribution assumptions, not the user’s live portfolio size
