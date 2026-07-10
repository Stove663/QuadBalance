## ADDED Requirements

### Requirement: Backtest primary period

The backtest engine SHALL simulate the candidate strategy over the primary period from 2013-01-01 to the latest available data date. For instruments with listing dates after 2013-01-01, simulation for that instrument MUST begin on its first available trading date, and the effective backtest start date MUST be reported.

#### Scenario: Full period simulation

- **WHEN** all primary instruments have data from 2013-01-01
- **THEN** the backtest runs from 2013-01-01 to the latest data date
- **AND** reports total years covered

#### Scenario: Late-listed QDII instrument

- **WHEN** 513500 data begins on 2014-01-15
- **THEN** the Stocks QDII sub-position simulation begins on 2014-01-15
- **AND** the report notes the effective start date per instrument

### Requirement: Backtest parameter sweep

The backtest engine MUST run a parameter sweep across: allocation variants (25/25/25/25, 20/30/25/25, 30/20/25/25, 20/25/30/25), bond variants (B1 5-year, B2 10-year, B3 50/50), DCA methods (proportional, underweight-priority), and rebalancing thresholds (±5%, ±10%). Each run MUST be identified by a unique configuration ID.

#### Scenario: Sweep produces comparable runs

- **WHEN** the sweep completes
- **THEN** each configuration ID has a full metrics report
- **AND** results are comparable on the same calendar period

### Requirement: Core performance metrics

For each backtest run, the engine SHALL compute: annualized return, annualized volatility, maximum drawdown (with date range), Sharpe ratio (risk-free rate = cash quadrant return), percentage of calendar years with positive return, and rebalancing premium (return difference vs buy-and-hold without rebalancing).

#### Scenario: Metrics reported per run

- **WHEN** a backtest run completes
- **THEN** the output includes all six core metrics
- **AND** maximum drawdown includes peak date and trough date

### Requirement: Benchmark comparison

Each backtest run SHALL be compared against three benchmarks: (1) CSI 300 buy-and-hold (510300), (2) traditional 60/40 portfolio (60% 510300 + 40% 511010), (3) cash-only (511880). The report MUST show relative return and relative max drawdown vs each benchmark.

#### Scenario: Benchmark relative performance

- **WHEN** the candidate strategy achieves 8% annualized return with 12% max drawdown
- **AND** the 60/40 benchmark achieves 7% annualized return with 18% max drawdown
- **THEN** the report shows +1% relative return and -6% relative max drawdown vs 60/40

### Requirement: Quadrant effectiveness check

The backtest report SHALL include a per-calendar-year table showing return of each quadrant and the combined portfolio. The report MUST highlight years where at least one quadrant had positive return while the portfolio drawdown was smaller than the worst single-quadrant drawdown.

#### Scenario: Diversification benefit year

- **WHEN** in calendar year Y Stocks return is -22%, Bonds +3%, Gold +9%, Cash +2%
- **THEN** the annual table records each quadrant return
- **AND** the portfolio return is computed and compared to the worst single-quadrant return

### Requirement: Stress test scenarios

The validation suite MUST include six stress scenarios applied to the locked candidate configuration:

| ID | Scenario | Parameters |
|----|----------|------------|
| S1 | A-share crash | Stocks -40% in one year, other quadrants at historical median |
| S2 | Stock-bond dual kill | Stocks -20%, Bonds 0%, Gold +10%, Cash +2% |
| S3 | CNY depreciation | CNY -10% vs USD; Gold +8%, QDII Stocks +12% (USD terms), domestic assets flat in CNY |
| S4 | Prolonged low rates | Bonds annual return capped at 2% for 5 consecutive years |
| S5 | QDII premium | 513500 purchases at 5% premium to NAV on every buy |
| S6 | Gold crash | Gold -20% in one year, other quadrants at historical median |

#### Scenario: Stress scenario S1 applied

- **WHEN** stress scenario S1 is executed on the candidate configuration
- **THEN** portfolio return for the stress year is computed
- **AND** compared to the -40% Stocks input shock

#### Scenario: Stress scenario S5 QDII premium

- **WHEN** stress scenario S5 is applied
- **THEN** every 513500 purchase in simulation pays 5% above NAV
- **AND** the report shows impact on total return vs baseline

### Requirement: Acceptance criteria

A candidate configuration SHALL pass validation and become eligible for strategy lock only when ALL of the following are met on the primary backtest period:

1. Maximum drawdown ≤ 25%
2. No single calendar year portfolio return below -20%
3. In every stress scenario S1–S6, portfolio drawdown is less than the worst single-quadrant shock input
4. Annualized return exceeds cash-only benchmark (511880) by at least 2%
5. Annualized return is not more than 2% below the 60/40 benchmark, OR max drawdown is at least 5% lower than the 60/40 benchmark

#### Scenario: Configuration passes all criteria

- **WHEN** a candidate achieves 10% annualized return, 18% max drawdown, worst year -12%
- **AND** all stress scenarios show portfolio outperforming worst single-quadrant shock
- **AND** return exceeds cash benchmark by 3%
- **AND** max drawdown is 8% lower than 60/40 benchmark
- **THEN** the configuration is marked "validation passed"

#### Scenario: Configuration fails drawdown criterion

- **WHEN** a candidate achieves 12% annualized return but 30% max drawdown
- **THEN** the configuration is marked "validation failed"
- **AND** the failure reason cites criterion 1 (max drawdown > 25%)

### Requirement: Strategy lock document

When a configuration passes validation, the system SHALL produce a strategy lock document containing: locked date, final allocation weights, primary instruments per quadrant, stocks sub-split (60/40), DCA method, rebalancing threshold, backtest period, all six core metrics, and stress test summary. The document MUST include a disclaimer that historical performance does not guarantee future results.

#### Scenario: Lock document generated on pass

- **WHEN** configuration "25-25-25-25_B1_prop_5pct" passes validation
- **THEN** a strategy lock document is generated with all required fields
- **AND** the investment-strategy configuration status changes from "candidate" to "locked"
