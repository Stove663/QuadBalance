# portfolio-backtest

## Purpose

Python backtest engine (QuadBalance) for validating China four-quadrant portfolio candidate configurations.

## Requirements

### Requirement: Fund data fetcher

The backtest engine SHALL fetch daily NAV or adjusted close prices for configured instruments using akshare. Off-exchange open-end funds MUST use `fund_open_fund_info_em`; on-exchange ETFs MAY use Sina ETF history as fallback. Fetched data MUST be cached locally in parquet files.

#### Scenario: Cache hit on second run

- **WHEN** fund data was previously fetched and cached
- **THEN** the engine loads data from local cache without network call

#### Scenario: Fetch missing OTC fund

- **WHEN** cache does not contain off-exchange fund 110020
- **THEN** the engine fetches NAV from akshare and writes to cache

### Requirement: Portfolio simulation

The simulator SHALL implement base position, monthly proportional DCA, and annual rebalancing per investment-strategy spec. Simulation MUST support allocation variants, bond variants, DCA methods, and rebalancing thresholds.

#### Scenario: Base position on start date

- **WHEN** simulation starts with base capital on the effective start date
- **THEN** capital is allocated across quadrants and sub-assets per configuration

#### Scenario: Annual rebalance triggered

- **WHEN** first trading day of a new year has quadrant drift exceeding threshold
- **THEN** trades are executed to restore target weights

### Requirement: CLI entry point

The system SHALL provide a CLI command `quadbalance` that runs the full parameter sweep, stress tests, acceptance evaluation, and writes output reports.

#### Scenario: Full validation run

- **WHEN** user runs `uv run quadbalance`
- **THEN** sweep results are written to output/sweep_results.csv
- **AND** strategy-lock.md is written if any configuration passes acceptance
