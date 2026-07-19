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

The simulator SHALL implement base position, monthly proportional DCA, and annual rebalancing per investment-strategy spec. Simulation MUST support allocation variants, bond variants, DCA methods, and rebalancing thresholds. QDII purchases MUST respect daily subscription quotas, pending cash handling, and backup routing defined in this capability. All buy and sell legs MUST apply per-symbol transaction fees from the instrument fee schedule. Rebalancing MUST propagate sell shortfalls and cap buy legs to available proceeds as defined in the rebalance sell shortfall propagation requirement.

#### Scenario: Base position on start date

- **WHEN** simulation starts with base capital on the effective start date
- **THEN** capital is allocated across quadrants and sub-assets per configuration
- **AND** QDII portion is subject to daily quota limits and backup routing
- **AND** each purchase applies that instrument's purchase fee rate

#### Scenario: Annual rebalance triggered

- **WHEN** first trading day of a new year has quadrant drift exceeding threshold
- **THEN** trades are executed to restore target weights within available sell proceeds
- **AND** QDII buy legs respect daily quota and pending cash rules
- **AND** sell and buy legs apply per-symbol fee rates
- **AND** any sell shortfalls are recorded rather than silently ignored

### Requirement: Rebalance sell shortfall propagation

During annual rebalancing, when a sell leg cannot raise the full target currency amount due to insufficient holdings, the simulator MUST record the shortfall and MUST NOT assume the full sell completed. Subsequent buy legs in the same rebalance MUST be limited to actual sell proceeds plus any explicitly provided extra cash.

#### Scenario: Sell shortfall reduces buy capacity

- **WHEN** rebalance attempts to sell 50,000 CNY of an instrument
- **AND** available holdings can raise only 30,000 CNY after fees
- **THEN** shortfall of 20,000 CNY is recorded for that sell event
- **AND** buy legs in the same rebalance are capped at 30,000 CNY plus extra cash

#### Scenario: No silent full execution on partial sell

- **WHEN** a sell shortfall occurs during rebalance
- **THEN** the simulator MUST NOT execute underweight buys as if the full sell amount were raised
- **AND** the shortfall event appears in simulation output

### Requirement: Rebalance execution metrics

Each backtest run SHALL report rebalance execution quality metrics: (1) count of sell shortfall events during rebalance, (2) total shortfall currency amount across all rebalance events, (3) maximum single-event shortfall amount, and (4) maximum post-rebalance quadrant weight deviation from target after any rebalance in the simulation period.

#### Scenario: Metrics included in sweep output

- **WHEN** a parameter sweep run completes
- **THEN** sweep_results.csv includes the four rebalance execution metrics for that configuration

#### Scenario: Shortfall events recorded with detail

- **WHEN** a rebalance sell shortfall occurs on date D for instrument X
- **THEN** simulation output records date D, instrument X, requested amount, raised amount, and shortfall amount

### Requirement: Per-symbol transaction fee schedule

The backtest engine SHALL apply per-symbol purchase and redemption fee rates on every simulated buy and sell. Fee rates MUST be resolved by the actual instrument symbol traded (including QDII backup substitutions). A global uniform transaction cost MUST NOT be used for simulation paths when a symbol-specific rate is defined.

#### Scenario: Domestic stock purchase uses fund-specific rate

- **WHEN** the simulator purchases 110020 with 60,000 CNY
- **THEN** the purchase fee rate is 0.12% (0.0012)
- **AND** shares acquired equal `60000 / (NAV × 1.0012)`

#### Scenario: Cash quadrant purchase has zero fee

- **WHEN** the simulator purchases 006874 with 25,000 CNY
- **THEN** the purchase fee rate is 0%
- **AND** shares acquired equal `25000 / NAV`

#### Scenario: QDII backup uses backup fund fee rate

- **WHEN** a QDII purchase is routed to backup 050025 because 161125 quota is exhausted
- **THEN** the purchase fee rate is 0.10% (0.0010), not 161125's 0.12%

### Requirement: OTC settlement lag

The portfolio simulator SHALL model off-exchange settlement lag for buys and sells. Share quantity from a buy MUST NOT be available for sale on the same trading day as the purchase. Sale proceeds MUST NOT be available for redeployment on the same trading day as the sale. Settlement completes on the next trading day in the simulation calendar (T+1 approximation).

#### Scenario: Same-day buy cannot be sold

- **WHEN** the simulator buys 110020 on date T
- **AND** a rebalance or sell attempts to sell that lot on date T
- **THEN** the newly purchased shares are not available
- **AND** only previously settled shares may be sold

#### Scenario: Sale proceeds deploy next day

- **WHEN** the simulator sells an instrument on date T
- **THEN** cash proceeds are not usable for buys on date T
- **AND** proceeds become available on the next trading day

### Requirement: Short-hold redemption fee schedule

The simulator SHALL track purchase lots FIFO per symbol and apply a short-hold redemption fee when the sold lot age is below a configurable holding window (default 7 calendar days). Instruments MUST declare a non-zero `redemption_rate` for equity, bond, and gold feeders where the product schedule has a short-term penalty; money-market cash MAY remain 0%. Universal zero redemption for all sells is forbidden.

#### Scenario: Recent lot sell incurs redemption fee

- **WHEN** shares of 000216 bought 3 days earlier are sold
- **AND** the instrument short-hold redemption rate is 0.005
- **THEN** proceeds equal `shares_sold × NAV × (1 - 0.005)`

#### Scenario: Seasoned lot sell has zero short-hold fee

- **WHEN** shares held longer than the short-hold window are sold
- **THEN** short-hold redemption fee is 0%
- **AND** only the seasoned-lot redemption rate (if any) applies

### Requirement: Redemption fee v1 assumption

Simulation SHALL apply the short-hold redemption fee schedule defined in this capability. The design MUST document the holding-window default and per-instrument short-hold rates. Blanket 0% redemption for all instruments and all holding periods is not permitted.

#### Scenario: Annual rebalance may still be zero fee

- **WHEN** rebalancing sells 003358 lots held longer than the short-hold window
- **THEN** short-hold redemption fee rate is 0%
- **AND** proceeds equal `shares_sold × NAV` absent other fees

#### Scenario: Underweight DCA churn can pay redemption

- **WHEN** underweight DCA causes a sell of a lot younger than the short-hold window
- **THEN** the configured short-hold redemption rate is applied

### Requirement: Transaction fee reporting

The strategy lock document SHALL include a Transaction Fee Assumptions section listing purchase fee rate per primary instrument and documenting the short-hold redemption schedule (window and rates), including which instruments have zero short-hold redemption.

#### Scenario: Lock document lists fee rates

- **WHEN** a configuration is lockable and strategy-lock.md is generated
- **THEN** the document includes purchase fee rates for 110020, 161125, 003358, 000216, and 006874
- **AND** states the short-hold redemption window and applicable rates rather than claiming universal 0% redemption

### Requirement: QDII daily subscription quota enforcement

The portfolio simulator SHALL enforce a configurable daily subscription cap for each QDII instrument on every purchase attempt (base position, DCA, and rebalance buys). When a buy request exceeds remaining daily quota for that instrument, the simulator MUST fill only up to the remaining quota and MUST NOT silently assume full execution. If the primary QDII instrument has no remaining quota, the simulator MUST attempt ranked backups in order before leaving any remainder as pending cash.

#### Scenario: DCA exceeds daily QDII cap

- **WHEN** monthly contribution allocates 1,000 CNY to QDII sub-position 161125 on a trading day
- **AND** configured daily cap for 161125 is 100 CNY
- **THEN** at most 100 CNY is executed as a purchase of 161125 on that day
- **AND** the unfilled amount is recorded as pending cash

#### Scenario: Quota resets each calendar day

- **WHEN** 161125 daily cap is 100 CNY and 100 CNY was already purchased on day T
- **AND** another buy for 161125 is attempted later on day T
- **THEN** no additional 161125 purchase is executed on day T
- **AND** the buy amount remains pending for day T+1

### Requirement: Pending cash ledger

The simulator SHALL maintain a pending cash balance for funds that could not be invested due to QDII quota limits. Pending cash MUST be applied to subsequent QDII purchase attempts on later trading days before new contribution cash is allocated to QDII, until the pending amount is fully invested or the simulation ends.

#### Scenario: Pending cash invested on next day

- **WHEN** 900 CNY remains pending after a quota-limited QDII buy on day T
- **AND** day T+1 has 100 CNY remaining daily quota for the active QDII instrument
- **THEN** 100 CNY of pending cash is used to purchase QDII on day T+1
- **AND** 800 CNY remains pending

#### Scenario: Pending cash included in portfolio value

- **WHEN** pending cash exists
- **THEN** daily portfolio value equals mark-to-market fund holdings plus pending cash balance

### Requirement: QDII backup routing on quota exhaustion

When the primary QDII instrument (161125) has no remaining daily quota for a purchase attempt, the simulator SHALL attempt the same purchase amount against the next ranked backup in the stocks QDII pool (050025, then 006075), subject to each backup's own daily cap and availability on the simulation date. Backup usage MUST be recorded in simulation output. Backups not yet listed on the simulation date MUST be skipped.

#### Scenario: Primary quota exhausted routes to backup

- **WHEN** 161125 daily cap is exhausted for day T
- **AND** a QDII purchase of 500 CNY is attempted
- **AND** backup 050025 has 500 CNY remaining daily cap
- **AND** day T is on or after 050025 inception
- **THEN** the purchase is executed against 050025 up to its cap
- **AND** the event is logged as a backup substitution

#### Scenario: Youngest backup skipped before inception

- **WHEN** day T is before 2018-06-08
- **AND** 161125 and 050025 daily caps are exhausted
- **THEN** 006075 is not attempted
- **AND** unfilled amount is recorded as pending cash

### Requirement: Price matrix alignment symbols

The data layer SHALL define a `PRICE_MATRIX_SYMBOLS` set containing primary strategy instruments and bond sweep columns only. QDII backup funds (050025, 006075) MUST NOT be included in this set. The effective backtest start date MUST be determined by `dropna(how="any")` on alignment symbols only. Callers that assemble symbol lists for alignment (including sweep `collect_required_symbols`) MUST NOT union QDII pool backup codes into that set.

#### Scenario: Alignment excludes QDII backups

- **WHEN** `load_price_matrix_with_meta()` loads prices with default symbols
- **THEN** the returned DataFrame columns do not include 050025 or 006075
- **AND** effective start is not constrained by 006075 listing date (2018-06-08)

#### Scenario: Restored long-history start

- **WHEN** all alignment symbols have proxy-stitched data from 2013-07-29 onward
- **THEN** the price matrix effective start is 2013-07-29 or earlier
- **AND** is not later than 2018-06-08 due to backup funds

#### Scenario: Sweep collect_required_symbols excludes backups

- **WHEN** `collect_required_symbols` runs for configs with QDII quota enabled
- **THEN** the returned list does not include 050025 or 006075
- **AND** those codes are requested only via backup price loading

### Requirement: Lazy QDII backup price loading

The data layer SHALL provide a function to load QDII backup fund prices independently of the alignment matrix. Backup prices MUST be cached in parquet like primary instruments. The simulator MUST join backup prices at runtime per trading day without requiring backup columns in the alignment `dropna` step.

#### Scenario: Backup prices loaded separately

- **WHEN** QDII quota simulation is enabled
- **THEN** 050025 and 006075 prices are available to the simulator via backup price lookup
- **AND** are not required columns in the alignment price matrix

#### Scenario: Backup unavailable on date

- **WHEN** simulation date is before 006075 inception
- **THEN** 006075 price is not joined into day prices
- **AND** routing skips 006075 without error

### Requirement: Date-aware QDII tradable pool

The simulator SHALL determine the active QDII instrument pool per trading day based on instrument inception dates. Before the primary QDII handoff date (161125 first NAV date), only the primary QDII column (161125, proxy-stitched) SHALL be tradable. After handoff, ranked backups become eligible in order. A backup MUST NOT be routed before its inception date.

#### Scenario: Proxy era single column

- **WHEN** simulation date is before 2016-12-02
- **THEN** QDII purchases execute only against the 161125 price column
- **AND** independent 050025 backup routing is not attempted

#### Scenario: Full pool after youngest backup lists

- **WHEN** simulation date is on or after 2018-06-08
- **THEN** QDII routing may use 161125, 050025, and 006075 subject to daily caps

### Requirement: Proxy-era QDII quota exemption

Daily QDII subscription quota enforcement MUST be disabled for trading dates before the primary QDII instrument (161125) handoff date, when the 161125 column uses proxy-stitched NAV. Quota enforcement MUST apply on and after the handoff date when `enable_qdii_quota` is true.

#### Scenario: No quota during proxy era

- **WHEN** simulation date is before 161125 handoff
- **AND** monthly contribution allocates 1,000 CNY to QDII
- **THEN** the full QDII amount executes against the 161125 column without daily cap
- **AND** no pending cash is created solely due to QDII quota

#### Scenario: Quota applies after handoff

- **WHEN** simulation date is on or after 161125 handoff
- **AND** daily cap for 161125 is 100 CNY
- **THEN** QDII quota rules apply as defined in existing requirements

### Requirement: QDII execution metrics

Each backtest run SHALL report QDII execution quality metrics: (1) QDII fill rate (executed QDII buys / intended QDII buys), (2) average pending cash balance, (3) maximum pending cash balance, (4) days with pending cash > 0, and (5) average actual QDII portfolio weight vs target QDII weight.

#### Scenario: Metrics included in sweep output

- **WHEN** a parameter sweep run completes with QDII quota simulation enabled
- **THEN** sweep_results.csv includes the five QDII execution metrics for that configuration

### Requirement: Proxy price perturbation

The data layer SHALL support applying annualized return drift to a specified date range of a price series without affecting dates outside that range. Perturbation MUST preserve the price level at the range boundary to maintain stitch continuity at handoff dates.

#### Scenario: Drift applied only to proxy segment

- **WHEN** a +2% annualized drift is applied to proxy segment ending 2016-12-02
- **THEN** only dates before 2016-12-02 are perturbed
- **AND** the price on 2016-12-02 matches the unperturbed handoff level

### Requirement: S4 bond return cap path modifier

The stress test module SHALL provide a function that clones the price matrix and caps bond instrument annual returns at a specified rate for a consecutive calendar-year window. The modifier MUST support B1, B2, and B3 bond variants by targeting the correct instrument columns.

#### Scenario: B1 bond cap applied for 5 years

- **WHEN** S4 is run for configuration with bond variant B1
- **AND** shock window is 2021–2025
- **THEN** instrument 003358 daily returns are scaled so each calendar year return ≤ 2%
- **AND** non-bond instruments retain original prices outside the scaling logic

### Requirement: Proxy sensitivity orchestration

The sweep orchestrator SHALL run proxy sensitivity analysis for the first configuration that passes acceptance criteria. Sensitivity runs MUST execute after the baseline sweep completes and reuse cached price data.

#### Scenario: Sensitivity runs for locked config only

- **WHEN** full validation completes and configuration `25-25-25-25_B1_prop_5pct` is locked
- **THEN** sensitivity analysis runs for that configuration only
- **AND** does not re-run the 48-configuration parameter sweep

### Requirement: CLI sensitivity flag

The CLI SHALL accept an optional `--full-sensitivity` flag that runs proxy sensitivity for all 48 configurations instead of only the locked configuration.

#### Scenario: Full sensitivity flag

- **WHEN** user runs `uv run quadbalance --full-sensitivity`
- **THEN** proxy_sensitivity.csv contains rows for all 48 configurations × all drift scenarios

### Requirement: CLI entry point

The system SHALL provide a CLI command `quadbalance` that runs the full parameter sweep, stress tests, acceptance evaluation, and writes output reports.

#### Scenario: Full validation run

- **WHEN** user runs `uv run quadbalance`
- **THEN** sweep results are written to output/sweep_results.csv
- **AND** strategy-lock.md is written if any configuration passes acceptance

### Requirement: ETF data fetcher

The backtest engine SHALL fetch daily adjusted close prices for ETFs 510300, 513500, 511010, 511260, 518880, and 511880 using akshare. Fetched data MUST be cached locally to avoid redundant network requests.

#### Scenario: Cache hit on second run

- **WHEN** ETF data was previously fetched and cached
- **THEN** the engine loads data from local cache without network call

#### Scenario: Fetch missing instrument

- **WHEN** cache does not contain instrument 510300
- **THEN** the engine fetches data from akshare and writes to cache






### Requirement: Reusable simulation execution within a sweep
The system SHALL reuse simulation results within a single sweep run when the simulation inputs and execution options are equivalent. The reuse key SHALL distinguish strategy configuration, rebalance mode, stress variant, price matrix identity, backup price inputs, and any simulation options that can affect results.

#### Scenario: Equivalent baseline simulation reused
- **WHEN** the sweep requests the same baseline simulation more than once for an equivalent configuration and data set
- **THEN** the later request reuses the previously computed result
- **AND** the returned portfolio path and simulation metrics are identical to a fresh simulation

#### Scenario: Incompatible simulation not reused
- **WHEN** the sweep requests a simulation with a different configuration, rebalance mode, stress variant, price matrix, or backup price input
- **THEN** the system treats it as a distinct simulation request
- **AND** no cached result from the incompatible request is used






### Requirement: Deferrable no-rebalance premium computation
The system SHALL allow broad sweep screening to defer the no-rebalance simulation used to calculate rebalance premium. When deferred, the system SHALL either mark the premium as unavailable for screening or compute it later for shortlisted and final-report configurations according to the selected runtime mode.

#### Scenario: Broad screening skips no-rebalance simulation
- **WHEN** the sweep runs in a mode that defers rebalance premium
- **THEN** each broad-screening candidate avoids the no-rebalance simulation
- **AND** validation logic does not depend on an exact rebalance premium unless it has been computed

#### Scenario: Final report includes exact rebalance premium
- **WHEN** a strategy is selected for final lock reporting
- **THEN** the system computes the no-rebalance simulation if it was previously deferred
- **AND** the final metrics include an exact rebalance premium






### Requirement: Configuration identity includes stock sub-split

Each simulated configuration MUST include the stock sub-split variant in its unique configuration ID so sweep rows remain comparable and unambiguous across sub-split variants.

#### Scenario: Distinct IDs for different stock splits

- **WHEN** two otherwise identical configurations differ only in stock sub-split (60/40 vs 50/50)
- **THEN** their configuration IDs differ
- **AND** both appear as separate rows in sweep results
