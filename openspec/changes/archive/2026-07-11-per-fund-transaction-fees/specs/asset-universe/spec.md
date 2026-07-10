## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Instrument metadata

Each instrument in the asset universe MUST be recorded with: fund code, quadrant assignment, role (primary), and account type (场外 / QDII where applicable). QDII instruments MUST additionally record simulated daily subscription cap and quota risk level for backtest configuration. Instruments used in simulation MUST additionally record machine-readable `TradeFees` with purchase and redemption rates.

#### Scenario: QDII instrument account requirement

- **WHEN** instrument 161125 is referenced in a trade
- **THEN** the system records that QDII subscription is required
- **AND** enforces configured daily quota limits in simulation
- **AND** flags trades that hit quota limits
- **AND** applies 161125's purchase fee rate of 0.12% on executed buys
