## ADDED Requirements

### Requirement: Price matrix alignment symbols

The data layer SHALL define a `PRICE_MATRIX_SYMBOLS` set containing primary strategy instruments and bond sweep columns only. QDII backup funds (050025, 006075) MUST NOT be included in this set. The effective backtest start date MUST be determined by `dropna(how="any")` on alignment symbols only.

#### Scenario: Alignment excludes QDII backups

- **WHEN** `load_price_matrix_with_meta()` loads prices with default symbols
- **THEN** the returned DataFrame columns do not include 050025 or 006075
- **AND** effective start is not constrained by 006075 listing date (2018-06-08)

#### Scenario: Restored long-history start

- **WHEN** all alignment symbols have proxy-stitched data from 2013-07-29 onward
- **THEN** the price matrix effective start is 2013-07-29 or earlier
- **AND** is not later than 2018-06-08 due to backup funds

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

## MODIFIED Requirements

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
