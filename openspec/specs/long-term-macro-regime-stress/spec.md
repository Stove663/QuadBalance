# long-term-macro-regime-stress Specification

## Purpose
Define deterministic long-term macro regime stress scenarios and the required reporting fields for locked strategies.

## Requirements
### Requirement: Long-term scenario catalog

The validation suite SHALL define three deterministic long-term macro regime scenarios that model multi-year environments where historical growth, rate, inflation, and mean-reversion assumptions may fail.

The scenario catalog MUST include at minimum:

| ID | Scenario | Horizon | Required assumptions |
|----|----------|---------|----------------------|
| LT1 | Prolonged stagflation | 10 years | weak equities, negative real bonds, elevated CPI, partial gold support, low real cash return |
| LT2 | Deflationary stagnation | 20 years | weak equities, low/negative CPI, near-zero cash yield, low bond yield after initial support, muted gold return |
| LT3 | Balance-sheet recession / Japanification | 30 years | compressed domestic equity returns, persistent low rates, private-sector deleveraging proxy, low/negative CPI phases, weak risk appetite, limited mean reversion |

Each scenario MUST document annual assumptions for Stocks, Bonds, Gold, Cash, CPI, and any QDII or currency friction used by the model.

#### Scenario: Scenario catalog is available

- **WHEN** long-term macro regime stress is run
- **THEN** LT1, LT2, and LT3 are available by stable IDs
- **AND** each scenario exposes its horizon and annual assumptions in machine-readable form

#### Scenario: Scenario assumptions are documented

- **WHEN** a long-term scenario is included in a report
- **THEN** the report lists the scenario horizon, CPI assumption, and quadrant return assumptions
- **AND** states that the scenario is deterministic stress evidence rather than a forecast

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

### Requirement: Long-term real-return metrics

For each long-term macro regime scenario, the validation suite SHALL compute nominal, real, drawdown, underwater, rolling-window, purchasing-power preservation, and withdrawal-risk metrics.

The metrics MUST include at minimum:

1. Nominal cumulative return.
2. Nominal annualized return.
3. Real cumulative return or real terminal wealth relative to initial wealth.
4. Real annualized return.
5. Maximum drawdown.
6. Longest underwater duration.
7. Worst rolling 5-year real return.
8. Worst rolling 10-year real return.
9. Whether purchasing power is preserved over the full horizon.
10. Whether a 4% withdrawal path depletes.

#### Scenario: LT2 real-return metrics are computed

- **WHEN** LT2 completes a 20-year simulation
- **THEN** the output includes nominal annualized return, real annualized return, maximum drawdown, longest underwater duration, and real terminal wealth
- **AND** the output marks whether purchasing power was preserved over the full 20-year horizon

#### Scenario: Rolling real-return failure is detected

- **WHEN** a long-term scenario has a rolling 10-year real return below the thesis-broken threshold
- **THEN** the scenario output records the worst rolling 10-year real return
- **AND** the governance classification is no better than `thesis-broken`

### Requirement: Long-term regime governance classification

The validation suite SHALL classify each long-term macro regime result as `normal`, `review-required`, or `thesis-broken` using deterministic governance thresholds.

Default classifications MUST follow these rules unless explicitly overridden by future profile thresholds:

1. `normal` when real annualized return is non-negative, real terminal wealth is at or above initial real wealth, longest underwater duration does not exceed 5 years, and no enabled withdrawal test depletes.
2. `review-required` when real annualized return is negative, real terminal wealth is below initial real wealth, or longest underwater duration exceeds 5 years without meeting thesis-broken thresholds.
3. `thesis-broken` when real terminal wealth loss exceeds 20%, longest underwater duration exceeds 10 years, worst rolling 10-year real return is below -10%, or a 4% real withdrawal path depletes.

#### Scenario: Review-required long-term result

- **WHEN** LT1 has negative real annualized return but real terminal wealth loss is not worse than 20%
- **THEN** LT1 is classified as `review-required`
- **AND** the report states which threshold caused the classification

#### Scenario: Thesis-broken long-term result

- **WHEN** LT3 has real terminal wealth loss greater than 20%
- **THEN** LT3 is classified as `thesis-broken`
- **AND** the strategy lock document requires re-validation before relying on the allocation for that regime

### Requirement: Long-term stress reporting in strategy lock

When long-term scenario results are available, the strategy lock document SHALL include a Long-Term Macro Regime Stress section listing each scenario's ID, name, horizon, nominal annualized return, real annualized return, maximum drawdown, longest underwater duration, purchasing-power preservation status, governance classification, and key threshold reasons.

#### Scenario: Strategy lock includes long-term summary

- **WHEN** LT1-LT3 complete for the locked configuration
- **THEN** strategy-lock.md includes a Long-Term Macro Regime Stress section
- **AND** each scenario row shows real-return, drawdown, underwater, purchasing-power, withdrawal, and governance classification fields

#### Scenario: Thesis-broken long-term regime is highlighted

- **WHEN** any long-term scenario is classified as `thesis-broken`
- **THEN** the strategy boundary summary includes the long-term regime classification
- **AND** the governance policy states that allocation redesign requires a new validation run rather than automatic parameter chasing

