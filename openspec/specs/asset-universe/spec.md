# asset-universe

## Purpose

Map each portfolio quadrant to tradable China-accessible off-exchange (场外) open-end fund instruments, including primary selections and the Stocks quadrant domestic/QDII sub-split.

## Requirements

### Requirement: Quadrant asset mapping

The asset universe SHALL map each portfolio quadrant to tradable off-exchange open-end funds. Each quadrant MUST have exactly one primary instrument per sub-position.

#### Scenario: Primary instruments for default strategy

- **WHEN** the default candidate strategy is configured
- **THEN** Stocks primary instruments are 110020 (60% of Stocks quadrant) and 161125 (40% of Stocks quadrant)
- **AND** Bonds primary instrument is 003358
- **AND** Gold primary instrument is 000216
- **AND** Cash primary instrument is 006874

### Requirement: Stocks quadrant domestic and global split

The Stocks quadrant SHALL allocate 60% to domestic CSI 300 feeder fund and 40% to S&P 500 QDII feeder fund. This yields approximately 10% of total portfolio in global equity exposure (25% × 40% = 10%).

#### Scenario: Stocks sub-allocation on purchase

- **WHEN** funds are allocated to the Stocks quadrant with amount S
- **THEN** 0.6 × S is used to purchase 110020
- **AND** 0.4 × S is used to purchase 161125

#### Scenario: Stocks sub-rebalance on annual check

- **WHEN** annual rebalancing adjusts the Stocks quadrant
- **THEN** the domestic and QDII sub-positions are rebalanced to 60/40 within the Stocks quadrant

### Requirement: Bonds quadrant with backtest alternatives

The Bonds quadrant primary instrument SHALL be 003358 (嘉实3-5年国债ETF联接A). The backtest engine MUST also support alternatives: 003327 (易方达中债7-10年国开行债券指数A) and a 50/50 blend of 003358 and 003327.

#### Scenario: Bonds primary in live execution

- **WHEN** the strategy is locked with default bond selection
- **THEN** 100% of the Bonds quadrant is held in 003358

#### Scenario: Bonds alternative in backtest sweep

- **WHEN** a backtest run specifies bond variant B2 (10-year)
- **THEN** 100% of the Bonds quadrant is simulated with 003327

### Requirement: Gold quadrant

The Gold quadrant SHALL use gold ETF feeder fund as the inflation hedge. Primary instrument: 000216 (华安黄金ETF联接A).

#### Scenario: Gold primary selection

- **WHEN** the default candidate strategy is configured
- **THEN** the Gold quadrant uses 000216 exclusively

### Requirement: Cash quadrant

The Cash quadrant SHALL use an off-exchange money market fund as the recession hedge. Primary instrument: 006874 (泰康现金管家货币A).

#### Scenario: Cash primary selection

- **WHEN** the default candidate strategy is configured
- **THEN** the Cash quadrant uses 006874 exclusively

### Requirement: Instrument backup pool

Each quadrant sub-position MUST maintain a ranked backup pool of at least two alternative funds. Backup selection SHALL prioritize: (1) subscription quota availability, (2) index tracking quality, (3) low purchase and holding cost. In backtest simulation, when a QDII purchase attempt exceeds available daily quota, the engine MUST automatically attempt ranked backups that are tradable on the simulation date before leaving funds as pending cash. QDII backup funds MAY use independent per-fund daily caps in simulation, but any shared-platform simplification MUST be documented in the backtest design.

#### Scenario: Primary fund quota exhausted

- **WHEN** primary fund 161125 has no available QDII subscription quota for the remainder of the day
- **AND** the simulation date is on or after the next ranked backup's inception date
- **THEN** the simulator attempts the next ranked backup from the stocks QDII pool (050025, then 006075 if listed)
- **AND** records the substitution in the strategy log

#### Scenario: Backup pool documented

- **WHEN** the strategy lock document is generated
- **THEN** it includes all primary and backup funds per quadrant with quota risk and cost notes
- **AND** includes observed QDII fill rate from the validating backtest run

### Requirement: QDII daily quota parameters

Each QDII instrument in the stocks QDII pool MUST declare a simulated daily subscription cap for backtesting. The default cap for primary 161125 SHALL be 100 CNY per calendar day unless overridden in configuration. Backup instruments SHALL declare their own caps (default: same as primary when unknown).

#### Scenario: Default primary QDII cap

- **WHEN** backtest runs with default QDII quota settings
- **THEN** 161125 has a simulated daily subscription cap of 100 CNY
- **AND** the cap value is recorded in run configuration output

#### Scenario: Configurable cap override

- **WHEN** a backtest run specifies `qdii_daily_cap=500` for 161125
- **THEN** the simulator uses 500 CNY as the daily cap for that run

### Requirement: QDII quota sharing across pool members

Backup QDII funds (050025, 006075) SHALL be modeled with independent daily caps in simulation. When multiple backups share platform QDII quota in live trading, the backtest MAY use conservative independent caps per fund; any simplification MUST be documented in design.md.

#### Scenario: Independent backup caps

- **WHEN** primary 161125 cap is exhausted
- **AND** backup 050025 is attempted
- **THEN** 050025 uses its own daily cap counter, not 161125's counter

### Requirement: Instrument metadata

Each instrument in the asset universe MUST be recorded with: fund code, quadrant assignment, role (primary), and account type (场外 / QDII where applicable). QDII instruments MUST additionally record simulated daily subscription cap and quota risk level for backtest configuration. Instruments used in simulation MUST additionally record machine-readable `TradeFees` with purchase and redemption rates.

#### Scenario: QDII instrument account requirement

- **WHEN** instrument 161125 is referenced in a trade
- **THEN** the system records that QDII subscription is required
- **AND** enforces configured daily quota limits in simulation
- **AND** flags trades that hit quota limits
- **AND** applies 161125's purchase fee rate of 0.12% on executed buys

### Requirement: Machine-readable trade fees

Each instrument in the asset universe that participates in backtest simulation MUST declare machine-readable trade fee rates via a `TradeFees` structure containing at minimum: `purchase_rate` (decimal, e.g. 0.0012 for 0.12%) and `redemption_rate` (decimal). Human-readable `purchase_fee` display strings MUST remain for strategy-lock documentation.

#### Scenario: Primary instruments have numeric fee rates

- **WHEN** instrument 110020 is loaded from the instrument pool
- **THEN** its `purchase_rate` is 0.0012
- **AND** its `redemption_rate` is 0.0 in v1

#### Scenario: QDII backup instruments have distinct fee rates

- **WHEN** backup 050025 is defined in the stocks QDII pool
- **THEN** its `purchase_rate` is 0.0010
- **WHEN** backup 006075 is defined in the stocks QDII pool
- **THEN** its `purchase_rate` is 0.0

### Requirement: Simulation symbol fee coverage

All fund codes returned by `simulation_symbols()` for a default strategy configuration MUST have an entry in the fee schedule. Missing fee data for a traded symbol SHALL cause simulation to fail fast with an explicit error.

#### Scenario: All QDII pool members have fees

- **WHEN** QDII quota simulation is enabled
- **THEN** fee rates exist for 161125, 050025, and 006075

### Requirement: Instrument validity check

On each annual rebalancing date, the system SHALL verify that all primary instruments remain available for subscription and redemption.

#### Scenario: Primary fund suspended

- **WHEN** primary fund 000216 is suspended before the annual check
- **THEN** the system records the suspension event in the strategy log

### Requirement: Instrument inception dates for simulation

Each instrument in the asset universe that participates in backtest simulation MUST have a recorded inception date (first available NAV or listing date). The backtest engine MUST use inception dates to gate tradability for QDII backup routing. Inception dates MAY be derived from cached price data with documented fallback constants.

#### Scenario: QDII backup inception recorded

- **WHEN** the asset universe is queried for QDII pool members
- **THEN** 161125, 050025, and 006075 each have an inception date
- **AND** 006075 inception is 2018-06-08 or the first cached NAV date

#### Scenario: Backup ineligible before inception

- **WHEN** simulation date is before 006075 inception
- **THEN** 006075 is not in the active tradable QDII pool for that date

### Requirement: QDII proxy handoff date

The asset universe MUST record the handoff date when primary QDII instrument 161125 replaces proxy-stitched NAV with its own NAV. Before this date, 161125 column prices represent proxy data; independent backup routing to 050025 MUST NOT create a parallel position in the same underlying.

#### Scenario: Handoff date defined

- **WHEN** backtest configuration references 161125 as primary QDII
- **THEN** handoff date is 2016-12-02 or the first available 161125 NAV date
- **AND** independent 050025 routing is disabled before handoff
