## MODIFIED Requirements

### Requirement: Quadrant asset mapping

The asset universe SHALL map each portfolio quadrant to tradable off-exchange open-end funds. Each quadrant MUST have exactly one primary instrument per sub-position. Default Stocks sub-weights remain 60% domestic / 40% QDII unless a configuration selects another supported stock sub-split variant.

#### Scenario: Primary instruments for default strategy

- **WHEN** the default candidate strategy is configured
- **THEN** Stocks primary instruments are 110020 (60% of Stocks quadrant) and 161125 (40% of Stocks quadrant)
- **AND** Bonds primary instrument is 003358
- **AND** Gold primary instrument is 000216
- **AND** Cash primary instrument is 006874

### Requirement: Stocks quadrant domestic and global split

The Stocks quadrant SHALL support configurable domestic/QDII sub-split variants. The default variant SHALL remain 60% domestic CSI 300 feeder and 40% S&P 500 QDII feeder. Supported MVP sweep variants MUST include at least: 60/40, 50/50, and 40/60 (domestic/QDII within the Stocks quadrant).

#### Scenario: Stocks sub-allocation on purchase

- **WHEN** funds are allocated to the Stocks quadrant with amount S under the active stock sub-split
- **THEN** domestic_share × S is used to purchase 110020
- **AND** qdii_share × S is used to purchase 161125
- **AND** domestic_share + qdii_share equals 1.0

#### Scenario: Stocks sub-rebalance on annual check

- **WHEN** annual rebalancing adjusts the Stocks quadrant
- **THEN** the domestic and QDII sub-positions are rebalanced to the configuration's active stock sub-split within the Stocks quadrant

#### Scenario: Default stock sub-split remains 60/40

- **WHEN** no stock sub-split variant is specified
- **THEN** the engine uses 60% domestic / 40% QDII
- **AND** for a 25% Stocks target, global equity exposure is approximately 10% of total portfolio
