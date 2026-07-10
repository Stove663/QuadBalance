## ADDED Requirements

### Requirement: Quadrant asset mapping

The asset universe SHALL map each portfolio quadrant to tradable China-accessible instruments. Each quadrant MUST have exactly one primary instrument and at least one backup instrument.

#### Scenario: Primary instruments for default strategy

- **WHEN** the default candidate strategy is configured
- **THEN** Stocks primary instruments are 510300 (60% of Stocks quadrant) and 513500 (40% of Stocks quadrant)
- **AND** Bonds primary instrument is 511010
- **AND** Gold primary instrument is 518880
- **AND** Cash primary instrument is 511880

### Requirement: Stocks quadrant domestic and global split

The Stocks quadrant SHALL allocate 60% to domestic A-share broad-market ETF and 40% to S&P 500 QDII ETF. This yields approximately 10% of total portfolio in global equity exposure (25% × 40% = 10%).

#### Scenario: Stocks sub-allocation on purchase

- **WHEN** funds are allocated to the Stocks quadrant with amount S
- **THEN** 0.6 × S is used to purchase 510300
- **AND** 0.4 × S is used to purchase 513500

#### Scenario: Stocks sub-rebalance on annual check

- **WHEN** annual rebalancing adjusts the Stocks quadrant
- **THEN** the domestic and QDII sub-positions are rebalanced to 60/40 within the Stocks quadrant

### Requirement: Bonds quadrant with backtest alternatives

The Bonds quadrant primary instrument SHALL be 5-year treasury bond ETF (511010). The backtest engine MUST also support alternatives: 10-year treasury bond ETF (511260) and a 50/50 blend of 511010 and 511260.

#### Scenario: Bonds primary in live execution

- **WHEN** the strategy is locked with default bond selection
- **THEN** 100% of the Bonds quadrant is held in 511010

#### Scenario: Bonds alternative in backtest sweep

- **WHEN** a backtest run specifies bond variant B2 (10-year)
- **THEN** 100% of the Bonds quadrant is simulated with 511260

### Requirement: Gold quadrant

The Gold quadrant SHALL use on-exchange gold ETF as the inflation hedge. Primary instrument: 518880 (Huaan Gold ETF). Backup: 159937 (Bosera Gold ETF).

#### Scenario: Gold primary selection

- **WHEN** the default candidate strategy is configured
- **THEN** the Gold quadrant uses 518880 exclusively

### Requirement: Cash quadrant

The Cash quadrant SHALL use on-exchange money market fund ETF as the recession hedge. Primary instrument: 511880 (Yinhua Daily ETF). Off-exchange money market funds MAY be documented as backup but are not the default for backtest simulation.

#### Scenario: Cash primary selection

- **WHEN** the default candidate strategy is configured
- **THEN** the Cash quadrant uses 511880 exclusively

### Requirement: Instrument metadata

Each instrument in the asset universe MUST be recorded with: ticker code, exchange, quadrant assignment, role (primary/backup), and account type required (A-share / QDII).

#### Scenario: QDII instrument account requirement

- **WHEN** instrument 513500 is referenced in a trade
- **THEN** the system records that QDII account access is required
- **AND** flags the trade if QDII constraints (premium, quota) apply in simulation

### Requirement: Instrument validity check

On each annual rebalancing date, the system SHALL verify that all primary instruments remain listed and tradable. If a primary instrument is delisted or suspended beyond a configurable grace period, the backup instrument for that quadrant SHALL be promoted.

#### Scenario: Primary ETF delisted

- **WHEN** primary ETF 518880 is delisted before the annual check
- **THEN** the system promotes backup 159937 to primary for the Gold quadrant
- **AND** records the promotion event in the strategy log
