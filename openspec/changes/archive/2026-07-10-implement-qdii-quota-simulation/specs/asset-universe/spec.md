## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Instrument backup pool

Each quadrant sub-position MUST maintain a ranked backup pool of at least two alternative funds. Backup selection SHALL prioritize: (1) subscription quota availability, (2) index tracking quality, (3) low purchase and holding cost. In backtest simulation, when primary QDII quota is exhausted on a purchase day, the engine MUST automatically attempt ranked backups before leaving funds as pending cash.

#### Scenario: Primary fund quota exhausted

- **WHEN** primary fund 161125 has no available QDII subscription quota for the remainder of the day
- **THEN** the simulator attempts the next ranked backup from the stocks QDII pool (050025, then 006075)
- **AND** records the substitution in the strategy log

#### Scenario: Backup pool documented

- **WHEN** the strategy lock document is generated
- **THEN** it includes all primary and backup funds per quadrant with quota risk and cost notes
- **AND** includes observed QDII fill rate from the validating backtest run

### Requirement: Instrument metadata

Each instrument in the asset universe MUST be recorded with: fund code, quadrant assignment, role (primary), and account type (场外 / QDII where applicable). QDII instruments MUST additionally record simulated daily subscription cap and quota risk level for backtest configuration.

#### Scenario: QDII instrument account requirement

- **WHEN** instrument 161125 is referenced in a trade
- **THEN** the system records that QDII subscription is required
- **AND** enforces configured daily quota limits in simulation
- **AND** flags trades that hit quota limits
