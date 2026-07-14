## MODIFIED Requirements

### Requirement: Portfolio simulation

The simulator SHALL implement base position, monthly proportional DCA, and annual rebalancing per investment-strategy spec. Simulation MUST support allocation variants, bond variants, DCA methods, rebalancing thresholds, and Stocks domestic/QDII sub-split variants. QDII purchases MUST respect daily subscription quotas, pending cash handling, and backup routing defined in this capability. All buy and sell legs MUST apply per-symbol transaction fees from the instrument fee schedule. Rebalancing MUST propagate sell shortfalls and cap buy legs to available proceeds as defined in the rebalance sell shortfall propagation requirement.

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

#### Scenario: Stock sub-split variant changes instrument targets

- **WHEN** a configuration uses stock sub-split 40/60 (domestic/QDII)
- **THEN** the simulator targets 40% of the Stocks quadrant to the domestic feeder and 60% to the QDII feeder
- **AND** QDII target weight of total portfolio equals stocks_weight × 0.60

## ADDED Requirements

### Requirement: Configuration identity includes stock sub-split

Each simulated configuration MUST include the stock sub-split variant in its unique configuration ID so sweep rows remain comparable and unambiguous across sub-split variants.

#### Scenario: Distinct IDs for different stock splits

- **WHEN** two otherwise identical configurations differ only in stock sub-split (60/40 vs 50/50)
- **THEN** their configuration IDs differ
- **AND** both appear as separate rows in sweep results
