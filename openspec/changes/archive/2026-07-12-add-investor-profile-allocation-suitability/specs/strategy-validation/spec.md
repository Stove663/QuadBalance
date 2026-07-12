# strategy-validation

## MODIFIED Requirements

### Requirement: Backtest parameter sweep

The backtest engine MUST run a parameter sweep across a broad set of allocation variants, including the classic permanent-portfolio styles (25/25/25/25, 20/30/25/25, 30/20/25/25, 20/25/30/25) and investor-suitability tilts (35/20/20/25, 40/20/20/20, 45/20/20/15, 50/20/15/15, 30/25/20/25, 20/30/20/30, 15/35/15/35), bond variants (B1 5-year, B2 10-year, B3 50/50), DCA methods (proportional, underweight-priority), and rebalancing thresholds (±5%, ±10%). Each run MUST be identified by a unique configuration ID.

#### Scenario: Sweep produces comparable runs

- **WHEN** the sweep completes
- **THEN** each configuration ID has a full metrics report
- **AND** results are comparable on the same calendar period
- **AND** investor-suitability allocation variants are included in the sweep output

## ADDED Requirements

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

The validation suite SHALL classify each candidate configuration for every default investor profile as `suitable`, `caution`, or `unsuitable`. The classification MUST be rule-based, deterministic, and accompanied by human-readable reasons. Suitability evaluation MUST use return, drawdown, real-return, lifecycle cashflow, behavioral, and execution-friction inputs.

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
