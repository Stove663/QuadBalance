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

The backtest engine MUST run a parameter sweep across: allocation variants (25/25/25/25, 20/30/25/25, 30/20/25/25, 20/25/30/25), investor-suitability allocation variants (35/20/20/25, 40/20/20/20, 45/20/20/15, 50/20/15/15, 30/25/20/25, 20/30/20/30, 15/35/15/35), bond variants (B1 5-year, B2 10-year, B3 50/50), DCA methods (proportional, underweight-priority), and rebalancing thresholds (±5%, ±10%). Each run MUST be identified by a unique configuration ID.

#### Scenario: Sweep produces comparable runs

- **WHEN** the sweep completes
- **THEN** each configuration ID has a full metrics report
- **AND** results are comparable on the same calendar period
- **AND** investor-suitability allocation variants are included in the sweep output

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

The validation suite MUST include short-horizon stress scenarios applied to the locked candidate configuration.

The scenario set MUST include at minimum:

| ID | Scenario | Parameters |
|----|----------|------------|
| S1 | A-share crash | Stocks -40% in one year, other quadrants at historical median |
| S2 | Stock-bond dual kill | Stocks -20%, Bonds 0%, Gold +10%, Cash +2% |
| S3 | CNY depreciation | CNY -10% vs USD; Gold +8%, QDII Stocks +12% (USD terms), domestic assets flat in CNY |
| S4 | Prolonged low rates | Bonds annual return capped at 2% for 5 consecutive calendar years (path simulation) |
| S5 | QDII premium | QDII purchases at 5% premium to NAV on every buy |
| S6 | Gold crash | Gold -20% in one year, other quadrants at historical median |
| S7 | Prolonged low QDII quota | QDII daily cap reduced to 10 CNY for the simulation window |
| S8 | Stagflation | Stocks -20%, Bonds -8%, Gold +5%, Cash +2%, CPI +6% |
| S9 | Global liquidity shock | Stocks -30%, Bonds -5%, Gold -10%, Cash +1%, QDII daily cap reduced to 10 CNY |
| S10 | CNY appreciation | CNY +10% vs USD; QDII stocks and gold flat in USD terms, domestic assets flat in CNY |
| S11 | Domestic inflation shock | CPI +8%, Stocks -10%, Bonds -8%, Gold +5%, Cash +2% |
| S12 | Multi-year quadrant stagnation | Stocks, Bonds, Gold, and Cash each fail to exceed CPI for 5 consecutive years |
| S13 | Persistent correlation/liquidity stress | Correlated defensive-asset drawdown with extended liquidity impairment |
| S14 | Quad hedge failure | All defensive quadrants lose hedge value and cash is haircut for inflation |
| S15 | Rebalance lockout | Rebalancing buys are delayed for one quarter |
| S16 | QDII FX/premium/quota triple shock | QDII suffers equity drawdown, FX reversal, premium compression, and quota scarcity |
| S17 | Silent inflation confiscation | Nominal drawdown can look mild while real wealth is impaired |
| S18 | Front-loaded crash after deployment | Large initial deployment is followed by a front-loaded crash |
| S19 | Bond fund redemption spiral | Bond fund faces redemption pressure and liquidity discount |
| S20 | Cash liquidity and inflation erosion | Cash-like fund liquidity is impaired and real cash return is negative |
| S21 | Behavioral capitulation | Investor capitulates after deep drawdown |

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
- **THEN** every QDII purchase in simulation pays 5% above NAV
- **AND** the report shows impact on total return vs baseline

#### Scenario: Stress scenario S7 low QDII quota

- **WHEN** stress scenario S7 is applied
- **THEN** every QDII purchase attempt uses a 10 CNY daily cap
- **AND** the report shows delta in total return and QDII fill rate vs baseline

#### Scenario: Long-term regime stress runs for locked configuration

- **WHEN** a configuration passes primary validation and is selected for strategy lock
- **THEN** the validation suite runs LT1, LT2, and LT3 for that locked configuration
- **AND** the results are available to the strategy lock document generator

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
3. Hard stress gates: no short-horizon, path, behavior, cross-border, or product-risk result classified `fail` or `thesis-broken` (including S1–S7 portfolio-vs-worst-quadrant checks where applicable). Results classified `review-required` do not fail this gate; they MUST be recorded as `needs_review`
4. Annualized return exceeds cash-only benchmark (511880) by at least 2%
5. Annualized return is not more than 2% below the 60/40 benchmark, OR max drawdown is at least 5% lower than the 60/40 benchmark

NAV recovery constraints that the implementation already applies as Criterion 3 hard gates remain hard failures when breached.

#### Scenario: Configuration passes all criteria

- **WHEN** a candidate achieves 10% annualized return, 18% max drawdown, worst year -12%
- **AND** no stress-family result is `fail` or `thesis-broken`
- **AND** return exceeds cash benchmark by 3%
- **AND** max drawdown is 8% lower than 60/40 benchmark
- **THEN** the configuration is marked "validation passed"
- **AND** any `review-required` findings appear only under `needs_review`

#### Scenario: Configuration fails drawdown criterion

- **WHEN** a candidate achieves 12% annualized return but 30% max drawdown
- **THEN** the configuration is marked "validation failed"
- **AND** the failure reason cites criterion 1 (max drawdown > 25%)

#### Scenario: Configuration fails only on thesis-broken extended stress

- **WHEN** a candidate meets metrics gates 1, 2, 4, and 5
- **AND** a cross-border or extended stress result is `thesis-broken`
- **THEN** the configuration is marked "validation failed"
- **AND** the failure reason cites that stress result

### Requirement: Review-required findings do not fail acceptance

Acceptance evaluation SHALL distinguish hard failures from review-required findings. A candidate MUST NOT fail `validation.passed` solely because a short-horizon stress, path stress, behavior stress, cross-border stress, or product-risk result is classified `review-required`. Those findings MUST be recorded on a dedicated `needs_review` list (or equivalent) and MUST appear in sweep output and the strategy lock document. A candidate MUST fail when any such result is classified `fail` or `thesis-broken`, subject to the same primary metrics gates (drawdown, worst year, NAV recovery, return vs cash and 60/40). Material `needs_review` findings MUST block `lockable` unless human sign-off is recorded per strategy-lock-integrity.

#### Scenario: Review-required stress does not block pass

- **WHEN** a candidate meets primary metrics gates
- **AND** all stress / path / behavior / cross-border / product-risk results are either `normal` or `review-required`
- **AND** none are `fail` or `thesis-broken`
- **THEN** the configuration is marked validation passed
- **AND** each `review-required` finding is listed in `needs_review`
- **AND** `failure_reasons` does not include those review-required findings

#### Scenario: Thesis-broken stress still blocks pass

- **WHEN** a candidate meets primary metrics gates
- **AND** any stress / path / behavior / cross-border / product-risk result is classified `fail` or `thesis-broken`
- **THEN** the configuration is marked validation failed
- **AND** the failure reason cites that scenario or boundary

#### Scenario: Sweep CSV exposes needs_review

- **WHEN** a sweep row is written for a deep-validated configuration with review-required findings
- **THEN** the row includes a `needs_review` field listing those findings
- **AND** `validation_passed` may still be true when `failure_reasons` is empty

#### Scenario: Sweep CSV exposes lockable

- **WHEN** a sweep row is written for a deep-validated configuration
- **THEN** the row includes a `lockable` boolean
- **AND** `lockable` is false when material `needs_review` is non-empty and no sign-off is attached

### Requirement: Alignment callers exclude QDII backups

Sweep and single-run market-data loading MUST NOT pass QDII backup symbols into the alignment price matrix. `collect_required_symbols` (and equivalents) MUST return primary/alignment symbols only. Backup symbols MUST be supplied solely through the backup price loading path. The engine MUST assert that alignment matrix columns do not intersect `QDII_BACKUP_SYMBOLS`.

#### Scenario: Sweep alignment start not truncated by 006075

- **WHEN** a full validation sweep loads market data for configurations with QDII quota enabled
- **THEN** the alignment price matrix columns exclude 050025 and 006075
- **AND** locked configuration `effective_start` is on or before 2013-08-01
- **AND** `effective_start` is not 2018-06-08

#### Scenario: Assertion fires on backup contamination

- **WHEN** a caller attempts to include 006075 in alignment symbols
- **THEN** loading fails fast with an explicit error naming the forbidden backup symbol

### Requirement: QDII quality gates beyond fill rate

Validation and lock eligibility MUST evaluate QDII execution quality using fill rate together with average QDII weight gap, pending-cash day count, and maximum post-rebalance deviation. A 100% fill rate MUST NOT clear material review when pending-cash days exceed 252 or average QDII weight remains more than 2 percentage points below target for at least 12 months, or when maximum post-rebalance deviation exceeds the configured rebalance threshold.

#### Scenario: Perfect fill with chronic pending is material review

- **WHEN** QDII fill rate is 100%
- **AND** pending-cash days exceed 252
- **THEN** validation records a material `needs_review` finding citing pending-cash duration
- **AND** fill rate alone does not suppress that finding

#### Scenario: Weight gap sustained 12 months is material review

- **WHEN** average actual QDII weight stays more than 2 percentage points below target for at least 12 months
- **THEN** a material `needs_review` finding is recorded

### Requirement: Suitability uses measured QDII metrics

Profile suitability classification invoked from validation MUST receive measured QDII fill rate, average QDII weight gap, and available friction/recovery metrics from the simulation result. Hardcoded perfect-execution defaults (fill rate 1.0 and weight gap 0.0) MUST NOT be used when simulation metrics exist.

#### Scenario: Validation passes real fill rate

- **WHEN** simulation reports fill rate 0.85 and average weight gap -0.03
- **THEN** `classify_suitability` is called with those measured values
- **AND** not with 1.0 and 0.0

### Requirement: Behavior stress dual evaluation

Behavioral stress rules MUST be evaluated on the historical portfolio path and ALSO against deep-drawdown proxies from path stress and selected short-horizon stresses (at least P1 maximum drawdown and S14 portfolio return as a drawdown surrogate). Strategy-lock behavior reporting MUST show both historical and stress-fed results. Risk Overview MUST NOT mark the behavior layer green solely because historical maximum drawdown never reached rule triggers when stress-fed evaluation was skipped.

#### Scenario: Historical shallow MDD still runs stress-fed rules

- **WHEN** historical maximum drawdown is milder than -10%
- **AND** P1 maximum drawdown is at or beyond a behavior rule trigger
- **THEN** stress-fed behavior evaluation records a triggered or classified result for that rule
- **AND** the lock document distinguishes historical vs stress-fed columns

### Requirement: Unrecovered end-sample drawdown is material

When maximum drawdown has no recovery date by the sample end, validation MUST record a material `needs_review` finding regardless of whether the drawdown depth is above or below -10%. Depth MAY still affect hard-fail vs review wording for other Criterion 3 gates, but open unrecovered drawdown at lock time MUST block `lockable` without sign-off.

#### Scenario: Open drawdown at sample end blocks lockable

- **WHEN** max drawdown trough has no recovery before the last simulation date
- **THEN** material `needs_review` includes unrecovered drawdown
- **AND** `lockable` is false without human sign-off

### Requirement: Lock selection prefers lockable candidates

Deterministic final lock selection MUST prefer `lockable` candidates. Configurations that are `validation.passed` but not `lockable` MUST NOT become the active strategy lock unless an explicit human sign-off is supplied for that configuration during the lock step.

#### Scenario: Soft-pass candidate skipped for lock

- **WHEN** multiple candidates pass validation
- **AND** only one is `lockable` without sign-off
- **THEN** the locked configuration is that lockable candidate

### Requirement: Outcome-based cross-border stress classification

Cross-border stress classification SHALL be based on measured portfolio outcomes for the candidate configuration. Scenario-definition parameters that are fixed for a scenario (including liquidity impairment months and capital mobility constraint months) MAY annotate reasons and MAY contribute to a `review-required` classification, but MUST NOT alone force `thesis-broken`. `thesis-broken` MUST require at least one outcome breach such as portfolio return below the severe return threshold or frozen external-asset weight at or above the severe frozen-weight threshold.

#### Scenario: CB3 is not automatically thesis-broken

- **WHEN** CB3 is evaluated for a configuration whose portfolio return is above the severe return threshold
- **AND** frozen external-asset weight is below the severe frozen-weight threshold
- **THEN** CB3 is classified `review-required` or `normal`, not `thesis-broken`
- **AND** prolonged impairment months may still be listed in reasons

#### Scenario: Severe frozen weight still thesis-broken

- **WHEN** a cross-border scenario yields frozen external-asset weight at or above the severe frozen-weight threshold
- **THEN** the scenario is classified `thesis-broken`
- **AND** acceptance marks the configuration failed when that result is included in evaluation

### Requirement: Correlation convergence and pseudo-diversification stress

The validation suite SHALL include a dedicated stress family that tests whether defensive quadrants fail together over an extended window after an initial diversification benefit disappears. This family is intended to capture the gap between ordinary market shocks and the failure of a supposedly diversified defensive mix when correlations rise.

The scenario family MUST report nominal portfolio return, CPI-adjusted return, maximum drawdown, longest underwater duration, and whether the portfolio preserved purchasing power over the full window.

The stress family MUST include at minimum:

| ID | Scenario | Parameters |
|----|----------|------------|
| S22 | Correlation convergence | Stocks, Bonds, Gold, and Cash all move toward the same negative return profile over a multi-year window |
| S23 | Defensive-asset co-crash | Bonds and Gold fall alongside Stocks while Cash real return is negative |
| S24 | Recovery-friction prolongation | Initial drawdown is followed by slow, uneven recovery that extends underwater duration materially |

#### Scenario: Correlation convergence stress is reported

- **WHEN** S22 is executed on a locked configuration
- **THEN** the report shows nominal return, CPI-adjusted return, max drawdown, and underwater duration
- **AND** marks the scenario as review-required or thesis-broken if all defensive quadrants lose diversification benefit simultaneously
- **AND** includes a reason when the result is materially worse than the baseline S13 persistent-correlation case

#### Scenario: Defensive-asset co-crash is reported

- **WHEN** S23 is executed on a locked configuration
- **THEN** the report shows whether Bonds, Gold, and Cash all contribute negatively in real terms
- **AND** the report explains whether the portfolio relied on pseudo-diversification that failed under stress
- **AND** the report identifies the dominant failing quadrant pair or trio when available

#### Scenario: Recovery-friction prolongation is reported

- **WHEN** S24 is executed on a locked configuration
- **THEN** the report shows the extended underwater duration relative to the baseline backtest
- **AND** the scenario is flagged if recovery time increases materially even when terminal return is acceptable
- **AND** the report distinguishes nominal recovery from real-value recovery

### Requirement: Cross-border execution and FX-rebalance interaction stress

The validation suite SHALL include explicit stress cases for cross-border execution friction that combine FX movement, QDII quota scarcity, premium/discount widening, and delayed rebalancing. These tests MUST be reported separately from short-horizon market shocks and MUST be traceable to the same QDII execution metrics used in the main validation report.

The scenario family MUST include at minimum:

| ID | Scenario | Parameters |
|----|----------|------------|
| S25 | QDII routing delay | QDII purchases are delayed by one or more rebalancing cycles |
| S26 | FX plus quota squeeze | QDII faces adverse FX movement plus reduced daily cap and elevated premium |
| S27 | Rebalance under cross-border stress | Rebalancing must restore target weights while cross-border execution is partially unavailable |

#### Scenario: QDII routing delay is reported

- **WHEN** S25 is executed on the locked configuration
- **THEN** the report shows impact on actual QDII fill rate, pending cash, average QDII weight gap, and total return
- **AND** identifies whether delayed routing causes material target-weight drift

#### Scenario: FX plus quota squeeze is reported

- **WHEN** S26 is executed on the locked configuration
- **THEN** the report shows the combined impact of FX movement, quota scarcity, and premium compression
- **AND** marks the scenario as thesis-broken if QDII exposure cannot be maintained through the stress window
- **AND** highlights whether the failure is driven primarily by FX, premium, quota, or delayed routing

#### Scenario: Rebalance under cross-border stress is reported

- **WHEN** S27 is executed on the locked configuration
- **THEN** the report shows whether rebalancing restores target allocations within the tolerance band
- **AND** the report notes any forced cash buildup or persistent underweighting of the QDII sleeve
- **AND** records any remaining drift after the final rebalance cycle

### Requirement: Product-concentration escalation in boundary reporting

The validation suite SHALL elevate product-concentration risk to a first-class validation boundary when a single sleeve or instrument accounts for a disproportionate share of implementation fragility. The boundary report MUST include the largest product-level contributor, its classification, and the reason the concentration is material. This requirement exists because a portfolio can look diversified at quadrant level while still being fragile at the fund-selection level.

#### Scenario: Concentrated sleeve is highlighted

- **WHEN** one product has a review-required or thesis-broken product-risk classification
- **THEN** the boundary report identifies that product as the dominant implementation risk
- **AND** explains whether the issue is concentration, liquidity, quota, valuation, or substitution risk
- **AND** links the finding back to the product-risk summary used by validation

### Requirement: Real-value preservation and recovery-time sensitivity reporting

The validation suite SHALL report nominal and CPI-adjusted outcomes together for all drawdown-heavy stress cases and path-dependent scenarios. The report MUST explicitly distinguish a strategy that recovers nominally from one that preserves purchasing power and recovers in acceptable time. This requirement is especially important for scenarios where bond, cash, or QDII sleeves appear stable in nominal terms but fail in real terms.

#### Scenario: Real-value preservation failure is reported

- **WHEN** a stress scenario has acceptable nominal return but negative real return
- **THEN** the report classifies the scenario as review-required at minimum
- **AND** includes the worst real-return window and longest underwater duration
- **AND** states whether cash-like or defensive sleeves were the source of real-value erosion

#### Scenario: Slow recovery is reported separately from terminal return

- **WHEN** a scenario produces acceptable terminal wealth but materially longer recovery time than baseline
- **THEN** the report marks recovery friction as a separate reason
- **AND** the strategy lock document includes the recovery-time sensitivity note
- **AND** the report compares underwater duration against the baseline backtest

### Requirement: Validation output includes uncovered risk summary

The strategy validation report SHALL include a short “uncovered risk summary” section listing scenario IDs and risk themes that remain under active review after the standard S1-S21 suite completes. This section MUST not change pass/fail outcomes by itself, but it MUST be visible in the locked strategy artifacts.

#### Scenario: Uncovered risk summary is emitted

- **WHEN** the validation suite finishes for a locked configuration
- **THEN** the output contains a summary of any newly added drawdown and stress-gap scenarios
- **AND** the summary names the risk themes they are intended to cover

### Requirement: Screening gate thresholds

The screening gate SHALL be defined using fast-to-compute thresholds derived from core metrics.

#### Scenario: Minimum screening conditions

- **WHEN** a candidate is screened
- **THEN** the screening gate SHALL evaluate at minimum real annualized return, max drawdown, and real terminal wealth
- **AND** candidates failing any of those thresholds SHALL not proceed to deep validation

### Requirement: Reusable precomputed intermediates

The sweep SHALL reuse precomputed market and benchmark intermediates across candidates within a single run.

#### Scenario: Multiple candidates share the same data slice

- **WHEN** multiple candidates use the same market history and benchmark series
- **THEN** the implementation SHALL compute invariant series once and reuse them for candidate evaluation
- **AND** repeated candidate evaluation SHALL NOT re-fetch or re-transform the same data unnecessarily

### Requirement: Ranked deep validation subset

The sweep SHALL support ranking candidates by a lightweight score before running deep validation, so that the most promising configurations are validated first.

#### Scenario: Many candidates remain after screening

- **WHEN** more candidates pass screening than are practical to fully validate within a reasonable time budget
- **THEN** the sweep SHALL prioritize deep validation for higher-ranked candidates first
- **AND** the ranking SHALL be derived from fast-to-compute metrics only

### Requirement: Deep validation budget

The sweep SHALL support a configurable budget for deep validation when the screened candidate set is large.

#### Scenario: Screened candidate set exceeds budget

- **WHEN** the number of screened candidates exceeds the deep validation budget
- **THEN** the sweep SHALL validate only the top-ranked candidates within the budget first
- **AND** the remaining candidates SHALL be deferred without changing the final selection rule for the validated set

### Requirement: Deterministic final lock selection

The optimization changes SHALL NOT alter which configuration is selected as the final lock when the same set of candidates reaches deep validation.

#### Scenario: Two runs over the same data

- **WHEN** the sweep runs twice over the same inputs
- **THEN** the final locked configuration and acceptance output SHALL remain deterministic
- **AND** the ordering of deep validation execution SHALL NOT affect the final selection

### Requirement: Strategy failure boundary assessment

The validation suite SHALL assess whether the locked candidate remains acceptable under explicit strategy-level failure boundaries covering macro regime failure, investor lifecycle mismatch, behavioral tolerance breach, and real-return erosion. These boundaries are not implementation bugs; they define conditions under which the investment thesis requires review before continued live use.

The assessment MUST include at minimum:

1. Macro regime boundaries: stagflation, global liquidity shock, CNY appreciation shock, and multi-quadrant low-return environment.
2. Lifecycle boundaries: accumulation with stable DCA, DCA interruption, no-new-contribution holding period, and retirement-style withdrawal period.
3. Behavioral boundaries: maximum drawdown tolerance, longest underwater duration, consecutive underperformance versus cash, and consecutive underperformance versus 60/40 benchmark.
4. Real-return boundaries: CPI-adjusted annualized return, worst rolling real return, and probability of failing to preserve purchasing power over rolling windows.

#### Scenario: Strategy boundary report generated

- **WHEN** a configuration passes primary validation
- **THEN** the validation suite generates a strategy boundary report for the locked configuration
- **AND** the report classifies each boundary as normal, review-required, or thesis-broken
- **AND** the strategy lock document includes a summary of review-required and thesis-broken boundaries

#### Scenario: Multi-quadrant low-return environment

- **WHEN** a scenario assumes Stocks, Bonds, Gold, and Cash each fail to exceed CPI for a 5-year window
- **THEN** the validation suite reports 5-year nominal return, 5-year real return, maximum drawdown, and underwater duration
- **AND** marks the strategy review-required if the portfolio fails to preserve purchasing power over the full window

### Requirement: Extended macro stress scenarios

The validation suite SHALL include additional strategy-level macro stress scenarios beyond S1-S7 to test environments where diversification may fail or where foreign-currency assets become a drag. These scenarios MUST be reported separately from execution-friction stress tests.

| ID | Scenario | Parameters |
|----|----------|------------|
| S8 | Stagflation | A-share Stocks -20%, QDII Stocks -15%, Bonds -8%, Gold +5%, Cash +2%, CPI +6% |
| S9 | Global liquidity shock | A-share Stocks -30%, QDII Stocks -30%, Bonds -5%, Gold -10%, Cash +1%, QDII daily cap reduced to 10 CNY |
| S10 | CNY appreciation | CNY +10% vs USD; QDII Stocks 0% USD return, Gold 0% USD return, domestic assets flat in CNY |
| S11 | Domestic inflation shock | CPI +8%, Stocks -10%, Bonds -8%, Gold +5%, Cash +2% |
| S12 | Multi-year quadrant stagnation | Stocks, Bonds, Gold, and Cash each earn no more than CPI for 5 consecutive years |

#### Scenario: Stagflation stress applied

- **WHEN** S8 is executed on the locked configuration
- **THEN** the report shows both nominal and CPI-adjusted portfolio return
- **AND** marks review-required if real portfolio return is below -10% for the stress year

#### Scenario: Global liquidity shock applied

- **WHEN** S9 is executed on the locked configuration
- **THEN** the report shows whether all non-cash quadrants decline simultaneously
- **AND** reports the additional effect of low QDII quota on actual QDII exposure

#### Scenario: CNY appreciation stress applied

- **WHEN** S10 is executed on the locked configuration
- **THEN** the report shows the CNY-denominated impact on QDII Stocks and Gold
- **AND** marks review-required if currency-sensitive assets create a portfolio loss despite flat domestic assets

### Requirement: Real-return and rolling-window metrics

For each backtest run, the validation suite SHALL compute real-return and path-pain metrics in addition to nominal core metrics. CPI data MAY be supplied from an external source or represented by documented annual assumptions when historical CPI data is unavailable.

The metrics MUST include:

1. CPI-adjusted annualized return.
2. CPI-adjusted terminal wealth.
3. Worst rolling 1-year, 3-year, and 5-year nominal returns.
4. Worst rolling 1-year, 3-year, and 5-year real returns.
5. Longest underwater duration measured from peak to full recovery.
6. Count of rolling 3-year and 5-year windows underperforming cash-only benchmark.
7. Count of rolling 3-year and 5-year windows underperforming 60/40 benchmark.
8. NAV recovery time or explicit unrecovered state.

#### Scenario: Real-return metrics included in output

- **WHEN** a backtest run completes
- **THEN** sweep_results.csv includes CPI-adjusted annualized return and worst rolling real returns
- **AND** the detailed report includes longest underwater duration

#### Scenario: Purchasing power failure detected

- **WHEN** a rolling 5-year window has negative real return
- **AND** the cash-only benchmark has positive real return over the same window
- **THEN** the report marks the window as a purchasing-power failure

### Requirement: Lifecycle cashflow stress tests

The validation suite SHALL test whether the locked strategy remains suitable under investor lifecycle cashflow changes. These lifecycle tests MUST be run after a configuration passes primary validation and MUST NOT be used to silently optimize the locked allocation.

The lifecycle tests MUST include:

1. No-DCA holding period: only the initial base position is invested.
2. DCA interruption: monthly contribution stops for 12, 24, and 36 months.
3. Bear-market DCA interruption: contribution stops immediately after portfolio drawdown exceeds 10%.
4. Retirement withdrawal: annual withdrawals of 3%, 4%, and 5% of initial portfolio value, inflation-adjusted each year.
5. Bear-market retirement start: withdrawals begin at the start of the worst historical drawdown window.
6. One-time liquidity need: a 20% portfolio withdrawal occurs during an existing drawdown.

#### Scenario: Retirement withdrawal stress applied

- **WHEN** the 4% inflation-adjusted withdrawal test is run
- **THEN** the report shows terminal wealth, maximum drawdown, real terminal wealth, and whether the portfolio depletes
- **AND** marks thesis-broken if the portfolio is depleted before the end of the backtest period

#### Scenario: DCA interruption after drawdown

- **WHEN** portfolio drawdown first exceeds 10%
- **AND** DCA is interrupted for 24 months
- **THEN** the report compares terminal wealth and recovery time versus the baseline DCA run
- **AND** marks review-required if recovery time increases by more than 24 months

### Requirement: Behavioral tolerance boundaries

The strategy lock document SHALL define behavioral tolerance boundaries that indicate when a human investor is likely to abandon the strategy. These boundaries MUST be reported as governance triggers rather than automatic allocation changes.

Default behavioral review triggers SHALL include:

1. Portfolio maximum drawdown exceeds 20%.
2. Portfolio remains underwater for more than 36 months.
3. Portfolio underperforms cash-only benchmark for 36 consecutive months.
4. Portfolio underperforms 60/40 benchmark for 60 consecutive months.
5. Portfolio has two consecutive calendar years with negative nominal return.
6. Actual QDII weight remains more than 2 percentage points below target for 12 consecutive months.

Default thesis-broken triggers SHALL include:

1. Portfolio maximum drawdown exceeds 30%.
2. Portfolio remains underwater for more than 60 months.
3. Portfolio underperforms cash-only benchmark for 60 consecutive months.
4. Rolling 5-year real return is below -10% while cash-only real return is non-negative.
5. QDII exposure cannot be restored to at least 50% of target for 24 consecutive months because of quota or product restrictions.

#### Scenario: Behavioral review trigger detected

- **WHEN** the portfolio remains underwater for 40 months
- **THEN** the strategy boundary report classifies the event as review-required
- **AND** the governance section states that the trigger requires review, not automatic strategy abandonment

#### Scenario: Thesis-broken trigger detected

- **WHEN** rolling 5-year real return is below -10%
- **AND** cash-only real return is non-negative over the same window
- **THEN** the strategy boundary report classifies the event as thesis-broken
- **AND** the strategy lock document requires an explicit re-validation before continuing live execution

### Requirement: Strategy governance policy

The strategy lock document SHALL include a governance policy defining how to respond when normal, review-required, or thesis-broken conditions occur. Governance actions MUST separate product replacement from asset-allocation redesign and MUST prevent frequent parameter chasing based on short-term performance.

The governance policy MUST include:

1. Normal condition: continue scheduled DCA and rebalancing without allocation changes.
2. Review-required condition: perform documented annual review, check whether the trigger is caused by product failure, execution friction, macro regime change, or investor lifecycle change, but do not change target allocation automatically.
3. Thesis-broken condition: freeze new optimization-based changes until a full re-validation is completed; allow risk-reduction actions only if explicitly documented.
4. Product replacement path: replace unavailable or unsuitable funds using pre-defined asset-universe criteria without changing quadrant target weights.
5. Allocation redesign path: change quadrant weights only through a new validation run and a new strategy lock document.
6. Cooldown rule: after any allocation redesign, the strategy MUST NOT be redesigned again for at least 12 months unless a thesis-broken trigger occurs.
7. Anti-chasing rule: underperformance versus a benchmark for less than 36 months MUST NOT by itself justify allocation changes.

#### Scenario: Product failure does not force allocation redesign

- **WHEN** a primary fund becomes unavailable for subscription
- **AND** an eligible backup fund exists in the same quadrant with acceptable cost and tracking quality
- **THEN** the governance policy allows product replacement within the same quadrant
- **AND** target quadrant weights remain unchanged

#### Scenario: Allocation redesign requires new validation

- **WHEN** a thesis-broken trigger is classified as caused by structural allocation failure
- **THEN** any proposed target-weight change requires a new parameter sweep, stress test set, and strategy lock document
- **AND** the old locked strategy remains archived for audit comparison

### Requirement: Strategy lock document

When a configuration passes validation, the system SHALL produce a strategy lock document containing: locked date, final allocation weights, primary instruments per quadrant, stocks sub-split (60/40), DCA method, rebalancing threshold, backtest period, all six core metrics, stress test summary, strategy boundary summary, governance policy, QDII execution summary, and long-term macro regime stress summary when available. The document MUST include a disclaimer that historical performance does not guarantee future results.

The lock document MUST render the stress summary with stable section headers matching the reporting helpers, including: `Stress Test Summary`, `Long-Term Macro Regime Stress`, `Risk Map Summary`, `Risk Overview Panel`, `One-Page Risk Summary`, `Dynamic Path Stress Tests`, `Behavioral Stress Rules`, `Cross-Border Access and Settlement Stress`, `Product-Level Risk`, and `Robustness and Valuation-Start Risk` when those inputs are present.

When a recovery-time metric is included, unrecovered paths MUST be rendered explicitly as `Unrecovered within test window` rather than assigned a synthetic duration.

#### Scenario: Lock document generated on pass

- **WHEN** configuration "25-25-25-25_B1_prop_5pct" passes validation
- **THEN** a strategy lock document is generated with all required fields
- **AND** the investment-strategy configuration status changes from "candidate" to "locked"

#### Scenario: Lock document includes governance policy

- **WHEN** a strategy lock document is generated
- **THEN** it includes normal, review-required, and thesis-broken condition definitions
- **AND** it states that review-required triggers do not automatically change allocation weights
- **AND** it states that allocation redesign requires new validation

### Requirement: Investor suitability metrics

For each backtest run, the validation suite SHALL compute investor suitability inputs sufficient to classify the configuration for accumulation, balanced core, pre-retirement preservation, and retirement withdrawal profiles.

The suitability inputs MUST include:

1. Nominal annualized return.
2. CPI-adjusted annualized return.
3. Maximum drawdown.
4. Longest underwater duration.
5. Worst rolling 3-year and 5-year real returns.
6. Consecutive underperformance versus cash-only benchmark.
7. Consecutive underperformance versus 60/40 benchmark.
8. QDII fill rate and actual QDII weight gap.
9. Lifecycle cashflow stress results relevant to the profile.

#### Scenario: Suitability inputs emitted

- **WHEN** a backtest run completes
- **THEN** sweep_results.csv includes profile suitability classifications
- **AND** the detailed report includes the metrics and reasons used for each classification

#### Scenario: QDII execution friction affects suitability

- **WHEN** actual QDII exposure remains more than 2 percentage points below target for 12 consecutive months
- **THEN** accumulation and balanced-core suitability classification includes an execution-friction warning
- **AND** if exposure cannot be restored to at least 50% of target for 24 consecutive months, the relevant profile classification is no better than `caution`

### Requirement: Trade-level lifecycle cashflow simulation

Lifecycle suitability tests SHALL be simulated through the portfolio trading engine rather than by post-processing a completed baseline value curve. The simulation MUST carry holdings forward over time and apply contributions, interruptions, withdrawals, fees, QDII quota limits, pending cash, and rebalancing according to deterministic rules.

#### Scenario: DCA interruption preserves existing holdings

- **WHEN** a 24-month DCA interruption scenario is run
- **THEN** existing holdings continue to fluctuate with market prices
- **AND** scheduled contributions are skipped during the interruption window
- **AND** the report compares terminal wealth and recovery time versus the uninterrupted baseline

#### Scenario: Retirement withdrawal sells assets deterministically

- **WHEN** a 4% inflation-adjusted retirement withdrawal scenario is run
- **THEN** scheduled withdrawals are deducted from portfolio value by using available cash first and then selling assets according to deterministic rules
- **AND** the simulation records terminal wealth, real terminal wealth, maximum drawdown, depletion status, and recovery time

#### Scenario: One-time liquidity need during drawdown

- **WHEN** a one-time 20% portfolio withdrawal occurs during an existing drawdown
- **THEN** the simulation records the post-withdrawal drawdown, recovery time, and whether the withdrawal forces asset sales below target weights

### Requirement: Profile suitability classification

The validation suite SHALL classify each candidate configuration for every default investor profile as `suitable`, `caution`, or `unsuitable`. The classification MUST be rule-based, deterministic, and accompanied by human-readable reasons.

#### Scenario: Accumulation suitability evaluated

- **WHEN** a configuration passes primary validation
- **AND** real annualized return is positive
- **AND** rolling 5-year real-return failure does not breach thesis-broken boundaries
- **AND** behavioral and execution-friction metrics remain within profile tolerance
- **THEN** the accumulation profile is classified as either `suitable` or `caution` based on relative real-return adequacy

#### Scenario: Pre-retirement suitability evaluated

- **WHEN** a configuration is evaluated for pre-retirement preservation
- **THEN** no-DCA, DCA-interruption, and one-time-liquidity scenarios are included in the classification
- **AND** the classification is `unsuitable` if those scenarios breach thesis-broken drawdown or recovery boundaries

#### Scenario: Retirement suitability evaluated

- **WHEN** a configuration is evaluated for retirement withdrawal
- **THEN** 3%, 4%, and 5% inflation-adjusted withdrawal tests are included in the classification
- **AND** depletion under the 4% withdrawal test classifies the retirement profile as `unsuitable`
- **AND** depletion only under the 5% withdrawal test classifies the retirement profile no better than `caution`

### Requirement: Suitability-aware strategy lock selection

When multiple configurations pass primary validation, the strategy lock process SHOULD select a configuration whose suitability classification matches the intended investor profile. If no intended profile is supplied, the strategy lock document MUST present the first passing configuration as mechanically valid but MUST not imply universal suitability.

#### Scenario: Intended profile supplied

- **WHEN** the user supplies an intended investor profile before strategy lock generation
- **AND** multiple configurations pass validation
- **THEN** the selected locked configuration prioritizes configurations classified as `suitable` for that profile
- **AND** tie-breaking remains deterministic and documented

#### Scenario: No intended profile supplied

- **WHEN** no intended investor profile is supplied
- **AND** a configuration passes validation
- **THEN** the lock document states that the locked configuration is mechanically valid
- **AND** lists profile-specific suitability classifications without claiming that the strategy is suitable for all investors

### Requirement: Staged sweep evaluation pipeline

The backtest engine MUST evaluate sweep candidates in stages so that more expensive analyses run only after cheaper gates succeed for that candidate.

Required stage order for each sweep candidate:

1. Historical portfolio simulation and core performance metrics.
2. Short-horizon / execution stress evaluation (S1–S21 family and related path tests used by acceptance).
3. Acceptance evaluation used for sweep pass/fail and lock ranking.

Long-term macro regime stress (LT1–LT3) MUST NOT run in the per-candidate deep path by default. It MUST run only after a configuration is selected for strategy lock, and only if that configuration has already completed primary validation including short-horizon stress.

Each sweep result row MUST record a validation stage that distinguishes at least screened-out candidates from deep-validated candidates.

#### Scenario: Failed metric screen skips stress and long-term

- **WHEN** a candidate fails the early metric screen
- **THEN** the engine does not run short-horizon stress for that candidate
- **AND** the engine does not run LT1–LT3 for that candidate
- **AND** the sweep row records a screened-out validation stage

#### Scenario: Deep-validated candidates skip per-candidate long-term

- **WHEN** a candidate passes the early metric screen and completes short-horizon stress plus acceptance evaluation
- **THEN** the sweep row is marked deep-validated
- **AND** LT1–LT3 are not executed as part of that candidate's worker evaluation by default

#### Scenario: Locked configuration receives long-term after stress

- **WHEN** at least one configuration passes primary validation and is selected for strategy lock
- **THEN** the engine runs LT1–LT3 for that locked configuration after short-horizon stress validation for it has completed
- **AND** the long-term results are attached before strategy-lock document generation

### Requirement: Long-term macro regime stress in strategy validation

When a configuration is selected for strategy lock, the validation suite SHALL run long-term macro regime stress scenarios for the locked configuration after primary sweep validation and short-horizon stress validation complete.

Long-term macro regime stress results MUST be reported separately from S1-S21 short-horizon and execution-friction stress tests. Long-term regime results MUST NOT silently change the selected allocation, but they MUST be included in the strategy boundary and governance evidence for the locked strategy.

The sweep MUST NOT run LT1–LT3 for every deep-validated candidate by default. Long-term scenarios are a lock-path governance analysis, not a per-candidate ranking input.

#### Scenario: Long-term regime stress runs for locked configuration

- **WHEN** a configuration passes primary validation and is selected for strategy lock
- **THEN** the validation suite runs LT1, LT2, and LT3 for that locked configuration
- **AND** the results are available to the strategy lock document generator

#### Scenario: Long-term regime stress does not affect sweep ranking

- **WHEN** multiple configurations pass primary validation
- **THEN** long-term macro regime stress is not run for every sweep candidate by default
- **AND** the selected locked allocation is not silently changed based on LT1-LT3 results

#### Scenario: Long-term is deferred until lock selection

- **WHEN** the parameter sweep evaluates the full candidate grid
- **THEN** worker evaluation for non-locked candidates omits LT1–LT3 by default
- **AND** LT1–LT3 execute at most once for the selected locked configuration in a normal sweep run

### Requirement: Long-term macro regime reporting in strategy lock document

The strategy lock document SHALL include a `Long-Term Macro Regime Stress` section when long-term scenario results are available.

The section MUST include for each long-term scenario: ID, scenario name, horizon, nominal annualized return, real annualized return, maximum drawdown, longest underwater duration, purchasing-power preservation status, governance classification, and key threshold reasons.

#### Scenario: Strategy lock includes long-term summary

- **WHEN** LT1-LT3 complete for the locked configuration
- **THEN** `strategy-lock.md` includes a `Long-Term Macro Regime Stress` section
- **AND** each scenario row shows real-return, drawdown, underwater, purchasing-power, and governance classification fields

#### Scenario: Thesis-broken long-term regime is highlighted

- **WHEN** any long-term scenario is classified as `thesis-broken`
- **THEN** the strategy boundary summary includes the long-term regime classification
- **AND** the governance policy states that allocation redesign requires a new validation run rather than automatic parameter chasing

### Requirement: Long-term macro regime reporting in strategy lock document

The strategy lock document SHALL include a `Long-Term Macro Regime Stress` section when long-term scenario results are available.

The section MUST include for each long-term scenario: ID, scenario name, horizon, nominal annualized return, real annualized return, maximum drawdown, longest underwater duration, purchasing-power preservation status, governance classification, and key threshold reasons.

#### Scenario: Strategy lock includes long-term summary

- **WHEN** LT1-LT3 complete for the locked configuration
- **THEN** `strategy-lock.md` includes a `Long-Term Macro Regime Stress` section
- **AND** each scenario row shows real-return, drawdown, underwater, purchasing-power, and governance classification fields

#### Scenario: Thesis-broken long-term regime is highlighted

- **WHEN** any long-term scenario is classified as `thesis-broken`
- **THEN** the strategy boundary summary includes the long-term regime classification
- **AND** the governance policy states that allocation redesign requires a new validation run rather than automatic parameter chasing

### Requirement: Long-term macro regime artifacts

The validation suite SHALL persist long-term macro regime stress outputs as run artifacts for auditability.

The artifacts MUST include a tabular summary of scenario metrics and SHOULD include detailed annual or daily path data when generated by the engine. Artifacts MUST record scenario assumptions so results can be reproduced without relying on hidden defaults.

#### Scenario: Long-term stress artifacts are written

- **WHEN** a locked configuration completes long-term macro regime stress
- **THEN** the output directory contains a long-term macro stress summary artifact
- **AND** the artifact includes scenario IDs, assumptions, metrics, classifications, and threshold reasons

#### Scenario: Artifacts preserve assumptions

- **WHEN** LT3 is written to artifacts
- **THEN** the artifact records the 30-year horizon and annual assumptions for Stocks, Bonds, Gold, Cash, and CPI
- **AND** records any QDII or currency friction assumption used by the scenario


### Requirement: Low QDII quota stress scenario

The validation suite MUST include stress scenario S7: prolonged QDII low quota. Parameters: primary QDII daily cap reduced to 10 CNY for the entire simulation period. The scenario SHALL report impact on total return and QDII fill rate vs baseline.

#### Scenario: S7 low quota stress applied

- **WHEN** stress scenario S7 is executed on the candidate configuration
- **THEN** every QDII purchase attempt uses a 10 CNY daily cap
- **AND** the report shows delta in annualized return and QDII fill rate vs baseline






### Requirement: S4 window-scoped evaluation mode
The system SHALL provide an explicit S4 evaluation mode that can choose between full-history exact path simulation and window-scoped path simulation. The selected mode SHALL be recorded with the S4 result.

#### Scenario: Full-history S4 preserves existing semantics
- **WHEN** S4 runs in full-history mode
- **THEN** the system applies the prolonged low-rate bond cap over the selected window within the full price history
- **AND** runs a full simulation before calculating the window cumulative return and pass/fail result

#### Scenario: Window-scoped S4 avoids full-history simulation
- **WHEN** S4 runs in window-scoped mode
- **THEN** the system evaluates only the selected S4 window price data
- **AND** calculates cumulative return, worst-year return, annualized window return, and pass/fail result from that window-scoped simulation
- **AND** the result indicates that window-scoped semantics were used






### Requirement: Approximate exploratory S5 and S7 stress
The system SHALL support an approximate stress mode for exploratory sweep screening. Approximate S5 and S7 stress SHALL estimate QDII premium and low-quota impact from existing simulation outputs without requiring full stress reruns, while exact stress SHALL remain the default for final validation.

#### Scenario: Approximate S5 avoids rerun
- **WHEN** exploratory stress mode is approximate
- **THEN** S5 QDII premium impact is estimated from existing portfolio exposure or QDII metrics
- **AND** the system does not rerun the full simulation solely for S5 during broad screening

#### Scenario: Approximate S7 avoids rerun
- **WHEN** exploratory stress mode is approximate
- **THEN** S7 low-quota impact is estimated from existing QDII fill, weight-gap, pending-cash, or related execution metrics
- **AND** the system does not rerun the full simulation solely for S7 during broad screening

#### Scenario: Exact final stress overrides exploratory approximation
- **WHEN** a candidate is selected for final lock validation
- **THEN** exact S5 and S7 stress simulations are run by default even if approximate stress was used during broad screening
- **AND** final validation pass/fail uses the exact stress results






### Requirement: Sweep results expose stock sub-split

Sweep output MUST include an explicit stock sub-split column (or equivalent field) so analysts can filter and compare domestic/QDII exposures without parsing configuration IDs.

#### Scenario: Stock sub-split column present

- **WHEN** the sweep completes
- **THEN** sweep_results.csv includes a stock sub-split field for every row
- **AND** values identify 60/40, 50/50, or 40/60
