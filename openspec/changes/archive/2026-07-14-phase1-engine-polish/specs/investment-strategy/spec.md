## MODIFIED Requirements

### Requirement: Recurring dollar-cost averaging

The strategy SHALL accept recurring contributions at a fixed calendar interval (default: monthly). Each contribution MUST be allocated across quadrants according to the active target weights (proportional DCA). The default contribution day is the first trading day of each month.

#### Scenario: Monthly proportional contribution

- **WHEN** a monthly contribution of amount C arrives on a contribution day
- **THEN** each quadrant receives C × target_weight_q for that quadrant
- **AND** sub-assets within the Stocks quadrant receive their configured stock sub-split weights

#### Scenario: Contribution with zero target weight quadrant

- **WHEN** a backtest variant sets any quadrant weight to 0%
- **THEN** that quadrant receives no contribution
- **AND** remaining quadrants receive contributions proportional to their weights

### Requirement: Investor profile definitions

The strategy SHALL define investor lifecycle profiles used to evaluate whether a mechanically valid allocation is suitable for a specific use case. Profile suitability MUST be treated as a strategy-selection constraint, not as a discretionary market-timing signal.

The default profiles SHALL include:

1. Accumulation: long horizon, stable DCA, no planned withdrawals, higher tolerance for volatility in exchange for real growth.
2. Balanced core: general-purpose household core allocation seeking moderate real return and controlled drawdown.
3. Pre-retirement preservation: shorter horizon before withdrawals, reduced tolerance for drawdown, increased liquidity concern.
4. Retirement withdrawal: no new contributions, recurring inflation-adjusted withdrawals, high sensitivity to sequence-of-returns risk and depletion.

Built-in numeric thresholds for each profile SHALL remain the default baseline. The system MUST accept optional profile-threshold overrides that replace selected numeric threshold fields for a run without mutating the built-in baseline definitions.

#### Scenario: Profiles available for suitability assessment

- **WHEN** the strategy validation suite evaluates a candidate configuration
- **THEN** the four default investor profiles are available for suitability assessment
- **AND** each profile exposes its objective, horizon assumption, contribution assumption, withdrawal assumption, and behavioral tolerance level

#### Scenario: Suitability does not override mechanical execution

- **WHEN** a profile is classified as caution or unsuitable for a locked configuration
- **THEN** the mechanical trade rules remain unchanged
- **AND** any target-weight change still requires a new validation run and a new strategy lock document

#### Scenario: Profile threshold overrides applied for a run

- **WHEN** the user supplies a valid profile-threshold override for one or more profiles
- **THEN** suitability classification uses the overridden thresholds for that run
- **AND** profiles without overrides continue to use built-in defaults
- **AND** the effective thresholds used are recorded in run artifacts and the strategy lock document

### Requirement: Profile-specific strategy suitability

The strategy SHALL classify each locked candidate configuration for every investor profile as `suitable`, `caution`, or `unsuitable`. The classification MUST be based on validation metrics, real-return metrics, lifecycle cashflow simulations, behavioral boundaries, and execution-friction metrics, evaluated against the effective profile thresholds for the run.

#### Scenario: Accumulation profile flags excessive defensiveness

- **WHEN** a configuration passes primary validation
- **AND** its long-run real return is positive but materially lower than higher-growth validated candidates
- **AND** its drawdown and behavioral metrics remain acceptable
- **THEN** the accumulation profile MAY be classified as `caution`
- **AND** the reason states that the allocation may be overly defensive for long-term accumulation

#### Scenario: Retirement profile rejects depletion

- **WHEN** a configuration passes primary validation
- **AND** its 4% inflation-adjusted retirement withdrawal simulation depletes before the end of the test period
- **THEN** the retirement withdrawal profile is classified as `unsuitable`
- **AND** the reason cites withdrawal depletion and sequence-risk failure

#### Scenario: Overridden drawdown threshold changes classification

- **WHEN** accumulation max-drawdown threshold is overridden to a stricter value
- **AND** a configuration's maximum drawdown breaches the overridden threshold but not the built-in default
- **THEN** the accumulation classification becomes `unsuitable` or `caution` according to the classification rules
- **AND** the reason cites the effective overridden threshold

## ADDED Requirements

### Requirement: Stocks sub-split as mechanical parameter

The strategy SHALL treat Stocks domestic/QDII sub-split as a mechanical configuration parameter alongside allocation weights, bond variant, DCA method, and rebalancing threshold. Once a configuration is locked, changing the stock sub-split REQUIRES a new validation run and a new strategy lock document.

#### Scenario: Locked stock sub-split is immutable

- **WHEN** a strategy is locked with stock sub-split 50/50
- **THEN** the lock document records domestic 50% / QDII 50% within Stocks
- **AND** changing to 60/40 or 40/60 requires a new change proposal and re-validation
