## ADDED Requirements

### Requirement: Instrument inception dates for simulation

Each instrument in the asset universe that participates in backtest simulation MUST have a recorded inception date (first available NAV or listing date). The backtest engine MUST use inception dates to gate tradability for QDII backup routing. Inception dates MAY be derived from cached price data with documented fallback constants.

#### Scenario: QDII backup inception recorded

- **WHEN** the asset universe is queried for QDII pool members
- **THEN** 161125, 050025, and 006075 each have an inception date
- **AND** 006075 inception is 2018-06-08 or the first cached NAV date

#### Scenario: Backup ineligible before inception

- **WHEN** simulation date is before 006075 inception
- **THEN** 006075 is not in the active tradable QDII pool for that date

### Requirement: QDII proxy handoff date

The asset universe MUST record the handoff date when primary QDII instrument 161125 replaces proxy-stitched NAV with its own NAV. Before this date, 161125 column prices represent proxy data; independent backup routing to 050025 MUST NOT create a parallel position in the same underlying.

#### Scenario: Handoff date defined

- **WHEN** backtest configuration references 161125 as primary QDII
- **THEN** handoff date is 2016-12-02 or the first available 161125 NAV date
- **AND** independent 050025 routing is disabled before handoff

## MODIFIED Requirements

### Requirement: Instrument backup pool

Each quadrant sub-position MUST maintain a ranked backup pool of at least two alternative funds. Backup selection SHALL prioritize: (1) subscription quota availability, (2) index tracking quality, (3) low purchase and holding cost. In backtest simulation, when a QDII purchase attempt exceeds available daily quota, the engine MUST automatically attempt ranked backups that are tradable on the simulation date before leaving funds as pending cash. QDII backup funds MAY use independent per-fund daily caps in simulation, but any shared-platform simplification MUST be documented in the backtest design.

#### Scenario: Primary fund quota exhausted

- **WHEN** primary fund 161125 has no available QDII subscription quota for the remainder of the day
- **AND** the simulation date is on or after the next ranked backup's inception date
- **THEN** the simulator attempts the next ranked backup from the stocks QDII pool (050025, then 006075 if listed)
- **AND** records the substitution in the strategy log

#### Scenario: Backup pool documented

- **WHEN** the strategy lock document is generated
- **THEN** it includes all primary and backup funds per quadrant with quota risk and cost notes
- **AND** includes observed QDII fill rate from the validating backtest run
