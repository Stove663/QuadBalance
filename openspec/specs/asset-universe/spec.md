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

Each quadrant sub-position MUST maintain a ranked backup pool of at least two alternative funds. Backup selection SHALL prioritize: (1) subscription quota availability, (2) index tracking quality, (3) low purchase and holding cost.

#### Scenario: Primary fund quota exhausted

- **WHEN** primary fund 161125 has no available QDII subscription quota
- **THEN** the investor SHALL use the next ranked backup from the stocks QDII pool (050025, then 006075)
- **AND** record the substitution in the strategy log

#### Scenario: Backup pool documented

- **WHEN** the strategy lock document is generated
- **THEN** it includes all primary and backup funds per quadrant with quota risk and cost notes

### Requirement: Instrument metadata

Each instrument in the asset universe MUST be recorded with: fund code, quadrant assignment, role (primary), and account type (场外 / QDII where applicable).

#### Scenario: QDII instrument account requirement

- **WHEN** instrument 161125 is referenced in a trade
- **THEN** the system records that QDII subscription is required
- **AND** flags the trade if QDII constraints (premium, quota) apply in simulation

### Requirement: Instrument validity check

On each annual rebalancing date, the system SHALL verify that all primary instruments remain available for subscription and redemption.

#### Scenario: Primary fund suspended

- **WHEN** primary fund 000216 is suspended before the annual check
- **THEN** the system records the suspension event in the strategy log
