## MODIFIED Requirements

### Requirement: Long-term synthetic path simulation

The validation suite SHALL convert long-term macro regime assumptions into deterministic synthetic price paths and run the locked portfolio configuration through the portfolio simulation engine.

Long-term synthetic path simulation MUST run for the locked configuration after primary historical validation and short-horizon stress validation for that configuration succeed. It MUST NOT be required for every sweep candidate by default.

The synthetic path builder MUST preserve the selected strategy configuration, DCA method, rebalancing threshold, transaction fees, QDII quota behavior, pending cash rules, and lifecycle-compatible portfolio mechanics where applicable. Quadrant-level assumptions MUST be applied consistently to all instruments assigned to that quadrant unless the scenario defines an explicit instrument-level override.

#### Scenario: Synthetic path drives portfolio engine

- **WHEN** LT3 is executed for a locked configuration
- **THEN** the engine generates a 30-year synthetic price path
- **AND** runs the strategy through the same simulation engine used for historical backtests
- **AND** reports path-dependent effects from DCA, rebalancing, fees, and QDII execution where applicable

#### Scenario: Instrument mapping follows quadrants

- **WHEN** a synthetic scenario supplies a Bonds annual return assumption
- **THEN** every instrument mapped to the Bonds quadrant uses that assumption unless the scenario defines an override
- **AND** the scenario output records which instruments received quadrant-level assumptions

#### Scenario: Sweep candidates do not require long-term paths by default

- **WHEN** a non-locked sweep candidate completes historical backtest and short-horizon stress evaluation
- **THEN** the engine does not require LT1–LT3 synthetic path simulation for that candidate by default
- **AND** long-term path simulation remains reserved for the locked configuration path
