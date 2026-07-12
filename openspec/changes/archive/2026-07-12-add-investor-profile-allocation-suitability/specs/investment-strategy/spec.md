# investment-strategy

## ADDED Requirements

### Requirement: Investor profile definitions

The strategy SHALL define investor lifecycle profiles used to evaluate whether a mechanically valid allocation is suitable for a specific use case. Profile suitability MUST be treated as a strategy-selection constraint, not as a discretionary market-timing signal.

The default profiles SHALL include:

1. Accumulation: long horizon, stable DCA, no planned withdrawals, higher tolerance for volatility in exchange for real growth.
2. Balanced core: general-purpose household core allocation seeking moderate real return and controlled drawdown.
3. Pre-retirement preservation: shorter horizon before withdrawals, reduced tolerance for drawdown, increased liquidity concern.
4. Retirement withdrawal: no new contributions, recurring inflation-adjusted withdrawals, high sensitivity to sequence-of-returns risk and depletion.

#### Scenario: Profiles available for suitability assessment

- **WHEN** the strategy validation suite evaluates a candidate configuration
- **THEN** the four default investor profiles are available for suitability assessment
- **AND** each profile exposes its objective, horizon assumption, contribution assumption, withdrawal assumption, and behavioral tolerance level

#### Scenario: Suitability does not override mechanical execution

- **WHEN** a profile is classified as caution or unsuitable for a locked configuration
- **THEN** the mechanical trade rules remain unchanged
- **AND** any target-weight change still requires a new validation run and a new strategy lock document

### Requirement: Profile-specific strategy suitability

The strategy SHALL classify each locked candidate configuration for every investor profile as `suitable`, `caution`, or `unsuitable`. The classification MUST be based on validation metrics, real-return metrics, lifecycle cashflow simulations, behavioral boundaries, and execution-friction metrics.

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

### Requirement: Suitability disclosure in strategy lock

The strategy lock document SHALL include an Investor Profile Suitability section. The section MUST list each default profile, its classification, and the key reasons for that classification. The document MUST state that profile suitability is a mechanical screen and is not personalized financial advice.

#### Scenario: Suitability section generated

- **WHEN** a configuration is locked
- **THEN** strategy-lock.md includes an Investor Profile Suitability section
- **AND** the section lists accumulation, balanced core, pre-retirement preservation, and retirement withdrawal classifications
- **AND** each classification includes at least one human-readable reason

#### Scenario: Unsuitable profile disclosed without auto-redesign

- **WHEN** one or more profiles are classified as `unsuitable`
- **THEN** the strategy lock document discloses the unsuitable profiles
- **AND** does not automatically change target allocation weights
- **AND** states that allocation redesign requires a new validation run
