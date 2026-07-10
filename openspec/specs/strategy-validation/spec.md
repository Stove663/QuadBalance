# strategy-validation

## Purpose

Define backtest methodology, stress test scenarios, performance metrics, acceptance criteria, and strategy lock document requirements for validating candidate portfolio configurations.

## Requirements

### Requirement: Backtest primary period

The backtest engine SHALL simulate the candidate strategy over the primary period from 2013-01-01 to the latest available data date. For instruments with listing dates after 2013-01-01, simulation for that instrument MUST begin on its first available trading date, and the effective backtest start date MUST be reported. QDII backup funds MUST NOT constrain the global price-matrix alignment start; only primary alignment symbols and their proxies determine the portfolio effective start.

#### Scenario: Full period simulation

- **WHEN** all primary alignment instruments have data from 2013-01-01
- **THEN** the backtest runs from 2013-01-01 to the latest data date
- **AND** reports total years covered

#### Scenario: Late-listed QDII backup does not truncate matrix

- **WHEN** QDII backup 006075 lists on 2018-06-08
- **AND** primary alignment symbols have data from 2013-07-29
- **THEN** portfolio effective_start is 2013-07-29 (or earliest common alignment date)
- **AND** is not truncated to 2018-06-08 by backup inclusion

#### Scenario: Late-listed QDII primary with proxy

- **WHEN** 161125 primary data begins on 2016-12-02 with 050025 proxy stitched before that date
- **THEN** the Stocks QDII sub-position simulation begins on proxy start date
- **AND** the report notes effective start and handoff date per instrument

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

The validation suite MUST include seven stress scenarios applied to the locked candidate configuration:

| ID | Scenario | Parameters |
|----|----------|------------|
| S1 | A-share crash | Stocks -40% in one year, other quadrants at historical median |
| S2 | Stock-bond dual kill | Stocks -20%, Bonds 0%, Gold +10%, Cash +2% |
| S3 | CNY depreciation | CNY -10% vs USD; Gold +8%, QDII Stocks +12% (USD terms), domestic assets flat in CNY |
| S4 | Prolonged low rates | Bonds annual return capped at 2% for 5 consecutive calendar years (path simulation) |
| S5 | QDII premium | 513500 purchases at 5% premium to NAV on every buy |
| S6 | Gold crash | Gold -20% in one year, other quadrants at historical median |
| S7 | Prolonged low QDII quota | QDII daily cap reduced to 10 CNY for entire simulation |

#### Scenario: Stress scenario S1 applied

- **WHEN** stress scenario S1 is executed on the candidate configuration
- **THEN** portfolio return for the stress year is computed
- **AND** compared to the -40% Stocks input shock

#### Scenario: Stress scenario S4 five-year path

- **WHEN** stress scenario S4 is applied
- **THEN** the engine re-runs full portfolio simulation on a modified price path
- **AND** bond instrument annual returns are capped at 2% for 5 consecutive calendar years
- **AND** the report shows 5-year cumulative portfolio return, worst single year in the window, and annualized return over the window

#### Scenario: Stress scenario S4 pass criterion

- **WHEN** S4 five-year path simulation completes with cumulative portfolio return of -8%
- **AND** the conservative floor is -10% (25% bonds weight × 2% × 5 years)
- **THEN** S4 is marked as passed

#### Scenario: Stress scenario S5 QDII premium

- **WHEN** stress scenario S5 is applied
- **THEN** every 513500 purchase in simulation pays 5% above NAV
- **AND** the report shows impact on total return vs baseline

#### Scenario: Stress scenario S7 low QDII quota

- **WHEN** stress scenario S7 is applied
- **THEN** every QDII purchase attempt uses a 10 CNY daily cap
- **AND** the report shows delta in total return and QDII fill rate vs baseline

### Requirement: QDII execution quality in validation output

The validation suite SHALL include QDII execution metrics in backtest output for every configuration. The strategy lock document MUST summarize QDII fill rate and maximum pending cash for the locked configuration, and SHOULD note the average actual QDII weight gap when it exceeds 2 percentage points of total portfolio.

#### Scenario: Lock document includes QDII friction summary

- **WHEN** a configuration passes validation with QDII quota simulation enabled
- **THEN** strategy-lock.md includes a QDII Execution section with fill rate and max pending cash
- **AND** notes if average actual QDII weight deviates from target by more than 2 percentage points of total portfolio

### Requirement: S4 path details in strategy lock document

The strategy lock document MUST include an S4 Five-Year Path section reporting: shock window years, 5-year cumulative portfolio return, worst single year in window, annualized return over window, and pass/fail status.

#### Scenario: Lock document S4 path section

- **WHEN** a locked configuration completes validation with S4 path simulation
- **THEN** strategy-lock.md includes the S4 Five-Year Path section with all four metrics
- **AND** lists the 5 calendar years used as the shock window

### Requirement: QDII era reporting in strategy lock

The strategy lock document MUST report QDII simulation era boundaries: proxy era end date (161125 handoff), and the date each backup fund becomes eligible for routing. When the restored backtest start precedes 161125 handoff, the document MUST note that QDII quota enforcement does not apply during the proxy era.

#### Scenario: Era boundaries in lock document

- **WHEN** a configuration passes validation after price-matrix alignment fix
- **THEN** strategy-lock.md includes QDII era dates (proxy end, backup eligibility)
- **AND** states whether quota applied from simulation start or from handoff date

### Requirement: Pre-fix regression check

After implementing price-matrix alignment fix, a full validation sweep MUST be re-run. The sweep output MUST record `effective_start` per configuration. At least one configuration MUST have `effective_start` on or before 2013-08-01 (restored long-history coverage).

#### Scenario: Start date restored

- **WHEN** full sweep completes after qdii-backup-price-matrix implementation
- **THEN** locked configuration effective_start is not 2018-06-08
- **AND** effective_start is on or before 2013-08-01

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
