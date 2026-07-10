## ADDED Requirements

### Requirement: ETF data fetcher

The backtest engine SHALL fetch daily adjusted close prices for ETFs 510300, 513500, 511010, 511260, 518880, and 511880 using akshare. Fetched data MUST be cached locally to avoid redundant network requests.

#### Scenario: Cache hit on second run

- **WHEN** ETF data was previously fetched and cached
- **THEN** the engine loads data from local cache without network call

#### Scenario: Fetch missing instrument

- **WHEN** cache does not contain instrument 510300
- **THEN** the engine fetches data from akshare and writes to cache

### Requirement: Portfolio simulation

The simulator SHALL implement base position, monthly proportional DCA, and annual rebalancing per investment-strategy spec. Simulation MUST support allocation variants, bond variants, DCA methods, and rebalancing thresholds.

#### Scenario: Base position on start date

- **WHEN** simulation starts with base capital on the effective start date
- **THEN** capital is allocated across quadrants and sub-assets per configuration

#### Scenario: Annual rebalance triggered

- **WHEN** first trading day of a new year has quadrant drift exceeding threshold
- **THEN** trades are executed to restore target weights

### Requirement: CLI entry point

The system SHALL provide a CLI command `portfolio-backtest` that runs the full parameter sweep, stress tests, acceptance evaluation, and writes output reports.

#### Scenario: Full validation run

- **WHEN** user runs `uv run portfolio-backtest`
- **THEN** sweep results are written to output/sweep_results.csv
- **AND** strategy-lock.md is written if any configuration passes acceptance
