## ADDED Requirements

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

### Requirement: Redemption fee v1 assumption

For v1 simulation, redemption fees SHALL be 0% for all instruments. The design MUST document that this assumes holdings exceed short-term redemption penalty windows at annual rebalance. Holding-period tiered redemption is explicitly deferred.

#### Scenario: Annual rebalance sell has zero redemption fee

- **WHEN** rebalancing sells 003358 to reduce bond overweight
- **THEN** redemption fee rate is 0%
- **AND** proceeds equal `shares_sold × NAV`

### Requirement: Transaction fee reporting

The strategy lock document SHALL include a Transaction Fee Assumptions section listing purchase fee rate per primary instrument and noting the v1 redemption assumption.

#### Scenario: Lock document lists fee rates

- **WHEN** a configuration passes validation and strategy-lock.md is generated
- **THEN** the document includes purchase fee rates for 110020, 161125, 003358, 000216, and 006874
- **AND** states redemption fees are modeled as 0% in v1

## MODIFIED Requirements

### Requirement: Portfolio simulation

The simulator SHALL implement base position, monthly proportional DCA, and annual rebalancing per investment-strategy spec. Simulation MUST support allocation variants, bond variants, DCA methods, and rebalancing thresholds. QDII purchases MUST respect daily subscription quotas, pending cash handling, and backup routing defined in this capability. All buy and sell legs MUST apply per-symbol transaction fees from the instrument fee schedule.

#### Scenario: Base position on start date

- **WHEN** simulation starts with base capital on the effective start date
- **THEN** capital is allocated across quadrants and sub-assets per configuration
- **AND** QDII portion is subject to daily quota limits and backup routing
- **AND** each purchase applies that instrument's purchase fee rate

#### Scenario: Annual rebalance triggered

- **WHEN** first trading day of a new year has quadrant drift exceeding threshold
- **THEN** trades are executed to restore target weights
- **AND** QDII buy legs respect daily quota and pending cash rules
- **AND** sell and buy legs apply per-symbol fee rates
