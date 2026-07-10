# investment-strategy

## Purpose

Define the mechanical execution rules for the China permanent portfolio: four-quadrant target allocation, base position entry, recurring contributions, annual rebalancing, and strategy lock gate.

## Requirements

### Requirement: Four-quadrant target allocation

The strategy SHALL divide the portfolio into four quadrants with equal default target weights: Stocks 25%, Bonds 25%, Gold 25%, Cash 25%. Each quadrant maps to one economic scenario: prosperity (stocks), deflation (bonds), inflation (gold), recession (cash).

#### Scenario: Default allocation sums to 100%

- **WHEN** the strategy is initialized with default parameters
- **THEN** the sum of quadrant target weights equals 100%
- **AND** each quadrant target weight is 25%

#### Scenario: Allocation variant for backtest sweep

- **WHEN** a backtest run specifies an allocation variant (e.g., 20/30/25/25)
- **THEN** the engine SHALL use the specified variant weights for that run
- **AND** the variant identifier SHALL be recorded in the run output

### Requirement: Base position entry

The strategy SHALL establish a base position by purchasing all four quadrants at target weights on the base-position date (T0). Base position MUST be executed as a single-day purchase without phasing or timing discretion.

#### Scenario: Base position on lock date

- **WHEN** the strategy lock date arrives and base capital is available
- **THEN** the system allocates base capital across four quadrants according to target weights
- **AND** each quadrant is fully purchased on the same trading day

#### Scenario: Insufficient base capital

- **WHEN** base capital is less than the minimum tradable unit for any quadrant ETF
- **THEN** the system SHALL report an error and SHALL NOT proceed with a partial base position

### Requirement: Recurring dollar-cost averaging

The strategy SHALL accept recurring contributions at a fixed calendar interval (default: monthly). Each contribution MUST be allocated across quadrants according to the active target weights (proportional DCA). The default contribution day is the first trading day of each month.

#### Scenario: Monthly proportional contribution

- **WHEN** a monthly contribution of amount C arrives on a contribution day
- **THEN** each quadrant receives C × target_weight_q for that quadrant
- **AND** sub-assets within the Stocks quadrant receive their configured sub-weights (60% domestic / 40% QDII)

#### Scenario: Contribution with zero target weight quadrant

- **WHEN** a backtest variant sets any quadrant weight to 0%
- **THEN** that quadrant receives no contribution
- **AND** remaining quadrants receive contributions proportional to their weights

### Requirement: Annual rebalancing

The strategy SHALL perform an annual rebalancing check on the first trading day of each calendar year. Rebalancing MUST be triggered when any quadrant's actual weight deviates from its target weight by more than the rebalancing threshold (default: ±5% absolute). When triggered, the strategy SHALL sell overweight quadrants and buy underweight quadrants to restore target weights.

#### Scenario: Rebalance triggered by drift

- **WHEN** the annual check finds Stocks at 32% with a 25% target and threshold ±5%
- **THEN** rebalancing is triggered
- **AND** Stocks are sold and underweight quadrants are bought until all quadrants are within threshold

#### Scenario: No rebalance within threshold

- **WHEN** the annual check finds all quadrants within ±5% of target
- **THEN** no trades are executed
- **AND** the check result is recorded as "no action"

#### Scenario: Rebalance prefers contribution over selling

- **WHEN** rebalancing is triggered and a monthly contribution occurs in the same period
- **THEN** the contribution funds SHALL be directed to underweight quadrants first
- **AND** selling of overweight quadrants SHALL occur only if contribution funds are insufficient

### Requirement: Mechanical execution without discretion

All buy, sell, and rebalance decisions MUST be fully determined by the configured rules and parameters. The strategy SHALL NOT incorporate macro forecasts, market timing, or discretionary overrides.

#### Scenario: Rule-driven trade on rebalance day

- **WHEN** rebalancing is triggered on the annual check date
- **THEN** trade orders are generated solely from target weights, actual weights, and threshold
- **AND** no external signal or manual input influences the trade list

### Requirement: Strategy lock gate

Final target allocation weights and primary asset selections MUST NOT be designated as "locked" until strategy-validation acceptance criteria pass. Prior to lock, all weights and assets are candidates subject to backtest and stress-test evaluation.

#### Scenario: Pre-lock configuration is candidate

- **WHEN** the strategy has not yet passed validation
- **THEN** configuration is labeled "candidate"
- **AND** changes to weights or primary assets do not require a new change proposal

#### Scenario: Post-lock configuration is immutable

- **WHEN** validation passes and the strategy is locked
- **THEN** target weights and primary assets are recorded in a strategy lock document
- **AND** any change to locked parameters requires a new change proposal and re-validation
