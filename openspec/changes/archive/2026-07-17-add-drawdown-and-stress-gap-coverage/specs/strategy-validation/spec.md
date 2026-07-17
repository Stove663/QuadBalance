# strategy-validation

## ADDED Requirements
### Requirement: Correlation convergence and pseudo-diversification stress

The validation suite SHALL include a dedicated stress family that tests whether defensive quadrants fail together over an extended window after an initial diversification benefit disappears. This family is intended to capture the gap between ordinary market shocks and the failure of a supposedly diversified defensive mix when correlations rise.

The scenario family MUST report nominal portfolio return, CPI-adjusted return, maximum drawdown, longest underwater duration, and whether the portfolio preserved purchasing power over the full window.

The stress family MUST include at minimum:

| ID | Scenario | Parameters |
|----|----------|------------|
| S22 | Correlation convergence | Stocks, Bonds, Gold, and Cash all move toward the same negative return profile over a multi-year window |
| S23 | Defensive-asset co-crash | Bonds and Gold fall alongside Stocks while Cash real return is negative |
| S24 | Recovery-friction prolongation | Initial drawdown is followed by slow, uneven recovery that extends underwater duration materially |

#### Scenario: Correlation convergence stress is reported

- **WHEN** S22 is executed on a locked configuration
- **THEN** the report shows nominal return, CPI-adjusted return, max drawdown, and underwater duration
- **AND** marks the scenario as review-required or thesis-broken if all defensive quadrants lose diversification benefit simultaneously
- **AND** includes a reason when the result is materially worse than the baseline S13 persistent-correlation case

#### Scenario: Defensive-asset co-crash is reported

- **WHEN** S23 is executed on a locked configuration
- **THEN** the report shows whether Bonds, Gold, and Cash all contribute negatively in real terms
- **AND** the report explains whether the portfolio relied on pseudo-diversification that failed under stress
- **AND** the report identifies the dominant failing quadrant pair or trio when available

#### Scenario: Recovery-friction prolongation is reported

- **WHEN** S24 is executed on a locked configuration
- **THEN** the report shows the extended underwater duration relative to the baseline backtest
- **AND** the scenario is flagged if recovery time increases materially even when terminal return is acceptable
- **AND** the report distinguishes nominal recovery from real-value recovery

### Requirement: Cross-border execution and FX-rebalance interaction stress

The validation suite SHALL include explicit stress cases for cross-border execution friction that combine FX movement, QDII quota scarcity, premium/discount widening, and delayed rebalancing. These tests MUST be reported separately from short-horizon market shocks and MUST be traceable to the same QDII execution metrics used in the main validation report.

The scenario family MUST include at minimum:

| ID | Scenario | Parameters |
|----|----------|------------|
| S25 | QDII routing delay | QDII purchases are delayed by one or more rebalancing cycles |
| S26 | FX plus quota squeeze | QDII faces adverse FX movement plus reduced daily cap and elevated premium |
| S27 | Rebalance under cross-border stress | Rebalancing must restore target weights while cross-border execution is partially unavailable |

#### Scenario: QDII routing delay is reported

- **WHEN** S25 is executed on the locked configuration
- **THEN** the report shows impact on actual QDII fill rate, pending cash, average QDII weight gap, and total return
- **AND** identifies whether delayed routing causes material target-weight drift

#### Scenario: FX plus quota squeeze is reported

- **WHEN** S26 is executed on the locked configuration
- **THEN** the report shows the combined impact of FX movement, quota scarcity, and premium compression
- **AND** marks the scenario as thesis-broken if QDII exposure cannot be maintained through the stress window
- **AND** highlights whether the failure is driven primarily by FX, premium, quota, or delayed routing

#### Scenario: Rebalance under cross-border stress is reported

- **WHEN** S27 is executed on the locked configuration
- **THEN** the report shows whether rebalancing restores target allocations within the tolerance band
- **AND** the report notes any forced cash buildup or persistent underweighting of the QDII sleeve
- **AND** records any remaining drift after the final rebalance cycle

### Requirement: Product-concentration escalation in boundary reporting

The validation suite SHALL elevate product-concentration risk to a first-class validation boundary when a single sleeve or instrument accounts for a disproportionate share of implementation fragility. The boundary report MUST include the largest product-level contributor, its classification, and the reason the concentration is material. This requirement exists because a portfolio can look diversified at quadrant level while still being fragile at the fund-selection level.

#### Scenario: Concentrated sleeve is highlighted

- **WHEN** one product has a review-required or thesis-broken product-risk classification
- **THEN** the boundary report identifies that product as the dominant implementation risk
- **AND** explains whether the issue is concentration, liquidity, quota, valuation, or substitution risk
- **AND** links the finding back to the product-risk summary used by validation

### Requirement: Real-value preservation and recovery-time sensitivity reporting

The validation suite SHALL report nominal and CPI-adjusted outcomes together for all drawdown-heavy stress cases and path-dependent scenarios. The report MUST explicitly distinguish a strategy that recovers nominally from one that preserves purchasing power and recovers in acceptable time. This requirement is especially important for scenarios where bond, cash, or QDII sleeves appear stable in nominal terms but fail in real terms.

#### Scenario: Real-value preservation failure is reported

- **WHEN** a stress scenario has acceptable nominal return but negative real return
- **THEN** the report classifies the scenario as review-required at minimum
- **AND** includes the worst real-return window and longest underwater duration
- **AND** states whether cash-like or defensive sleeves were the source of real-value erosion

#### Scenario: Slow recovery is reported separately from terminal return

- **WHEN** a scenario produces acceptable terminal wealth but materially longer recovery time than baseline
- **THEN** the report marks recovery friction as a separate reason
- **AND** the strategy lock document includes the recovery-time sensitivity note
- **AND** the report compares underwater duration against the baseline backtest

### Requirement: Validation output includes uncovered risk summary

The strategy validation report SHALL include a short “uncovered risk summary” section listing scenario IDs and risk themes that remain under active review after the standard S1-S21 suite completes. This section MUST not change pass/fail outcomes by itself, but it MUST be visible in the locked strategy artifacts.

#### Scenario: Uncovered risk summary is emitted

- **WHEN** the validation suite finishes for a locked configuration
- **THEN** the output contains a summary of any newly added drawdown and stress-gap scenarios
- **AND** the summary names the risk themes they are intended to cover
