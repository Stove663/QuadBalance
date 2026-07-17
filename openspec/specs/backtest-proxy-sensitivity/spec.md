# backtest-proxy-sensitivity

## Purpose

Quantify how proxy-fund tracking error affects backtest conclusions and report performance split by proxy vs primary fund eras.

## Requirements

### Requirement: Proxy tracking error sensitivity scenarios

The backtest engine SHALL run deterministic tracking-error sensitivity scenarios for each configured backtest proxy mapping. For each proxy instrument segment (pre-handoff period), the engine MUST apply annualized return drift adjustments of +1%, +2%, -1%, and -2% independently per proxy mapping, holding all other series at baseline.

#### Scenario: Independent drift on QDII proxy

- **WHEN** sensitivity analysis runs for proxy mapping 161125 ← 050025
- **AND** a +2% annualized drift is applied to the 050025 segment only
- **THEN** the engine produces a full simulation result for the locked configuration
- **AND** records the scenario identifier `161125_proxy_+2pct`

#### Scenario: Baseline included in sensitivity set

- **WHEN** sensitivity analysis completes
- **THEN** results include the unperturbed baseline alongside all drift scenarios
- **AND** each scenario is uniquely identified

### Requirement: Sensitivity metrics output

For each sensitivity scenario, the engine SHALL compute: annualized return, maximum drawdown, Sharpe ratio, worst calendar year return, and whether the configuration would still pass acceptance criteria 1–5.

The baseline row MUST be included in the output set and identified by the `baseline` scenario ID.

#### Scenario: Sensitivity metrics per scenario

- **WHEN** a drift scenario simulation completes
- **THEN** the output row includes all five sensitivity metrics
- **AND** includes a `validation_passed` boolean for that scenario

### Requirement: Segmented era reporting

The engine SHALL report performance metrics split by calendar era: `proxy_era` (2013-01-01 through 2016-12-31) and `primary_era` (2017-01-01 through latest data date). Each era MUST report annualized return, maximum drawdown, and positive years percentage.

If the effective backtest start is after 2016-12-31, the proxy era metrics MAY be omitted and the report SHALL note that the proxy era is not covered.

#### Scenario: Proxy era metrics reported

- **WHEN** the backtest period covers 2013 through 2026
- **THEN** `proxy_era` metrics are computed using only daily values from 2013-01-01 to 2016-12-31
- **AND** `primary_era` metrics are computed from 2017-01-01 onward

#### Scenario: Short era excluded gracefully

- **WHEN** the effective backtest start is after 2016-12-31
- **THEN** `proxy_era` metrics are omitted
- **AND** the report notes that the proxy era is not covered

### Requirement: Sensitivity summary for strategy lock

The strategy lock document MUST include a Proxy Sensitivity Summary section showing: baseline metrics, min/max annualized return across drift scenarios, min/max max drawdown across drift scenarios, and the proxy mapping whose drift causes the largest absolute impact on annualized return.

#### Scenario: Lock document sensitivity summary

- **WHEN** a locked configuration completes sensitivity analysis
- **THEN** strategy-lock.md includes the Proxy Sensitivity Summary section
- **AND** identifies the most impactful proxy mapping

### Requirement: Sensitivity output files

The validation run SHALL write `output/proxy_sensitivity.csv` with one row per sensitivity scenario and `output/segment_metrics.csv` with one row per calendar era segment.

Both files MUST include `config_id` as the first column. `proxy_sensitivity.csv` MUST include `scenario_id`, `primary_symbol`, `annual_drift`, `annualized_return`, `max_drawdown`, `sharpe_ratio`, `worst_year_return`, and `validation_passed`. `segment_metrics.csv` MUST include `era`, `start`, `end`, `annualized_return`, `max_drawdown`, and `positive_years_pct`.

#### Scenario: CSV files written on full run

- **WHEN** user runs `uv run quadbalance`
- **THEN** `output/proxy_sensitivity.csv` is created for the locked configuration
- **AND** `output/segment_metrics.csv` is created with proxy_era and primary_era rows
