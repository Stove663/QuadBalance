## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Portfolio simulation

The simulator SHALL implement base position, monthly proportional DCA, and annual rebalancing per investment-strategy spec. Simulation MUST support allocation variants, bond variants, DCA methods, and rebalancing thresholds. QDII purchases MUST respect daily subscription quotas, pending cash handling, and backup routing defined in this capability. Rebalancing MUST propagate sell shortfalls and cap buy legs to available proceeds as defined in the rebalance sell shortfall propagation requirement.

#### Scenario: Base position on start date

- **WHEN** simulation starts with base capital on the effective start date
- **THEN** capital is allocated across quadrants and sub-assets per configuration
- **AND** QDII portion is subject to daily quota limits and backup routing

#### Scenario: Annual rebalance triggered

- **WHEN** first trading day of a new year has quadrant drift exceeding threshold
- **THEN** trades are executed to restore target weights within available sell proceeds
- **AND** QDII buy legs respect daily quota and pending cash rules
- **AND** any sell shortfalls are recorded rather than silently ignored
