## MODIFIED Requirements

### Requirement: Backtest parameter sweep

The backtest engine MUST run a parameter sweep across: allocation variants (25/25/25/25, 20/30/25/25, 30/20/25/25, 20/25/30/25), investor-suitability allocation variants (35/20/20/25, 40/20/20/20, 45/20/20/15, 50/20/15/15, 30/25/20/25, 20/30/20/30, 15/35/15/35), bond variants (B1 5-year, B2 10-year, B3 50/50), DCA methods (proportional, underweight-priority), rebalancing thresholds (±5%, ±10%), and Stocks domestic/QDII sub-split variants (60/40, 50/50, 40/60). Each run MUST be identified by a unique configuration ID that includes the stock sub-split.

#### Scenario: Sweep produces comparable runs

- **WHEN** the sweep completes
- **THEN** each configuration ID has a full metrics report
- **AND** results are comparable on the same calendar period
- **AND** investor-suitability allocation variants are included in the sweep output
- **AND** stock sub-split variants 60/40, 50/50, and 40/60 are included in the sweep output

### Requirement: Strategy lock document

When a configuration passes validation, the system SHALL produce a strategy lock document containing: locked date, final allocation weights, primary instruments per quadrant, the selected stocks sub-split (domestic/QDII), DCA method, rebalancing threshold, backtest period, all six core metrics, stress test summary, strategy boundary summary, governance policy, investor profile suitability, and the effective profile thresholds used for classification. The document MUST include a disclaimer that historical performance does not guarantee future results.

#### Scenario: Lock document generated on pass

- **WHEN** configuration "25-25-25-25_B1_prop_5pct_s60-40" passes validation
- **THEN** a strategy lock document is generated with all required fields
- **AND** the stocks sub-split field matches the locked configuration
- **AND** the investment-strategy configuration status changes from "candidate" to "locked"

#### Scenario: Lock document includes governance policy

- **WHEN** a strategy lock document is generated
- **THEN** it includes normal, review-required, and thesis-broken condition definitions
- **AND** it states that review-required triggers do not automatically change allocation weights
- **AND** it states that allocation redesign requires new validation

#### Scenario: Lock document records effective profile thresholds

- **WHEN** a strategy lock document is generated after a run that used profile-threshold overrides
- **THEN** the document discloses which thresholds were overridden
- **AND** lists the effective numeric thresholds used for each profile classification

### Requirement: Suitability-aware strategy lock selection

When multiple configurations pass primary validation, the strategy lock process MUST select exactly one locked configuration using a deterministic multi-key ranking. If an intended investor profile is supplied, the primary key SHALL be suitability rank for that profile (`suitable` > `caution` > `unsuitable`). Remaining tie-break keys SHALL be applied in fixed order: higher annualized return, lower absolute maximum drawdown, higher QDII fill rate, then lexicographic configuration ID ascending. If no intended profile is supplied, suitability rank is skipped and the remaining keys decide among all primary-passing configurations; the lock document MUST present the result as mechanically valid and MUST NOT imply universal suitability.

#### Scenario: Intended profile supplied

- **WHEN** the user supplies an intended investor profile before strategy lock generation
- **AND** multiple configurations pass validation
- **THEN** the selected locked configuration prioritizes configurations classified as `suitable` for that profile
- **AND** ties among equal suitability ranks are broken by the documented multi-key order

#### Scenario: No intended profile supplied

- **WHEN** no intended investor profile is supplied
- **AND** multiple configurations pass validation
- **THEN** selection uses the documented non-profile tie-break keys only
- **AND** the lock document states that the locked configuration is mechanically valid
- **AND** lists profile-specific suitability classifications without claiming that the strategy is suitable for all investors

#### Scenario: Lexicographic config ID breaks final ties

- **WHEN** two passing configurations are equal on all preceding ranking keys
- **THEN** the configuration with the lexicographically smaller configuration ID is locked
- **AND** the selection is stable across identical re-runs

## ADDED Requirements

### Requirement: Sweep results expose stock sub-split

Sweep output MUST include an explicit stock sub-split column (or equivalent field) so analysts can filter and compare domestic/QDII exposures without parsing configuration IDs.

#### Scenario: Stock sub-split column present

- **WHEN** the sweep completes
- **THEN** sweep_results.csv includes a stock sub-split field for every row
- **AND** values identify 60/40, 50/50, or 40/60
