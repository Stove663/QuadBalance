# strategy-validation

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Strategy lock document

When a configuration passes validation, the system SHALL produce a strategy lock document containing: locked date, final allocation weights, primary instruments per quadrant, stocks sub-split (60/40), DCA method, rebalancing threshold, backtest period, all six core metrics, stress test summary, strategy boundary summary, and governance policy. The document MUST include a disclaimer that historical performance does not guarantee future results.

#### Scenario: Lock document generated on pass

- **WHEN** configuration "25-25-25-25_B1_prop_5pct" passes validation
- **THEN** a strategy lock document is generated with all required fields
- **AND** the investment-strategy configuration status changes from "candidate" to "locked"

#### Scenario: Lock document includes governance policy

- **WHEN** a strategy lock document is generated
- **THEN** it includes normal, review-required, and thesis-broken condition definitions
- **AND** it states that review-required triggers do not automatically change allocation weights
- **AND** it states that allocation redesign requires new validation
