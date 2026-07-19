## ADDED Requirements

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

## MODIFIED Requirements

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
