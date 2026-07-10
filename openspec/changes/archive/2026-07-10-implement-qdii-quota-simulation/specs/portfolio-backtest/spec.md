## ADDED Requirements

### Requirement: QDII daily subscription quota enforcement

The portfolio simulator SHALL enforce a configurable daily subscription cap for each QDII instrument on every purchase attempt (base position, DCA, and rebalance buys). When a buy request exceeds remaining daily quota for that instrument, the simulator MUST fill only up to the remaining quota and MUST NOT silently assume full execution.

#### Scenario: DCA exceeds daily QDII cap

- **WHEN** monthly contribution allocates 1,000 CNY to QDII sub-position 161125 on a trading day
- **AND** configured daily cap for 161125 is 100 CNY
- **THEN** at most 100 CNY is executed as a purchase of 161125 on that day
- **AND** the unfilled amount is recorded as pending cash

#### Scenario: Quota resets each calendar day

- **WHEN** 161125 daily cap is 100 CNY and 100 CNY was already purchased on day T
- **AND** another buy for 161125 is attempted later on day T
- **THEN** no additional 161125 purchase is executed on day T
- **AND** the buy amount remains pending for day T+1

### Requirement: Pending cash ledger

The simulator SHALL maintain a pending cash balance for funds that could not be invested due to QDII quota limits. Pending cash MUST be applied to subsequent QDII purchase attempts on later trading days before new contribution cash is allocated to QDII, until the pending amount is fully invested or the simulation ends.

#### Scenario: Pending cash invested on next day

- **WHEN** 900 CNY remains pending after a quota-limited QDII buy on day T
- **AND** day T+1 has 100 CNY remaining daily quota for the active QDII instrument
- **THEN** 100 CNY of pending cash is used to purchase QDII on day T+1
- **AND** 800 CNY remains pending

#### Scenario: Pending cash included in portfolio value

- **WHEN** pending cash exists
- **THEN** daily portfolio value equals mark-to-market fund holdings plus pending cash balance

### Requirement: QDII backup routing on quota exhaustion

When the primary QDII instrument (161125) has no remaining daily quota for a purchase attempt, the simulator SHALL attempt the same purchase amount against the next ranked backup in the stocks QDII pool (050025, then 006075), subject to each backup's own daily cap. Backup usage MUST be recorded in simulation output.

#### Scenario: Primary quota exhausted routes to backup

- **WHEN** 161125 daily cap is exhausted for day T
- **AND** a QDII purchase of 500 CNY is attempted
- **AND** backup 050025 has 500 CNY remaining daily cap
- **THEN** the purchase is executed against 050025 up to its cap
- **AND** the event is logged as a backup substitution

### Requirement: QDII execution metrics

Each backtest run SHALL report QDII execution quality metrics: (1) QDII fill rate (executed QDII buys / intended QDII buys), (2) average pending cash balance, (3) maximum pending cash balance, (4) days with pending cash > 0, and (5) average actual QDII portfolio weight vs target QDII weight.

#### Scenario: Metrics included in sweep output

- **WHEN** a parameter sweep run completes with QDII quota simulation enabled
- **THEN** sweep_results.csv includes the five QDII execution metrics for that configuration

## MODIFIED Requirements

### Requirement: Portfolio simulation

The simulator SHALL implement base position, monthly proportional DCA, and annual rebalancing per investment-strategy spec. Simulation MUST support allocation variants, bond variants, DCA methods, and rebalancing thresholds. QDII purchases MUST respect daily subscription quotas, pending cash handling, and backup routing defined in this capability.

#### Scenario: Base position on start date

- **WHEN** simulation starts with base capital on the effective start date
- **THEN** capital is allocated across quadrants and sub-assets per configuration
- **AND** QDII portion is subject to daily quota limits and backup routing

#### Scenario: Annual rebalance triggered

- **WHEN** first trading day of a new year has quadrant drift exceeding threshold
- **THEN** trades are executed to restore target weights
- **AND** QDII buy legs respect daily quota and pending cash rules
