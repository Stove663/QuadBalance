## ADDED Requirements

### Requirement: Three-slot return-seeking lock shortlist

When a deep validation sweep completes with one or more soft-pass configurations (`validation.passed`) and zero naturally `lockable` configurations, the system SHALL build a lock shortlist of up to three roles: `primary`, `max_return_contrast`, and `step_down`. The shortlist MUST NOT mark any candidate as the active strategy lock. Each shortlist entry MUST include at least: `config_id`, role, annualized return, max drawdown, `pending_cash_days`, stock sub-split, allocation name, `lockable` (false until sign-off), material `needs_review` list, and a short pros/cons summary distinguishing shared universal reviews from differential frictions.

#### Scenario: Shortlist after zero lockable

- **WHEN** a sweep finishes with soft-passes and no `lockable` configuration
- **THEN** the system produces a three-role shortlist artifact (or fewer roles only when a role cannot be filled)
- **AND** no active strategy-lock document is written solely because the shortlist was built

#### Scenario: Natural lockable skips shortlist path

- **WHEN** at least one configuration is `lockable` after sweep validation (and long-term veto handling)
- **THEN** the system may lock via existing lockable preference
- **AND** MUST NOT require the return-seeking shortlist path for that run

### Requirement: Primary prefers return band then lower pending

For the `primary` role under the return-seeking preference, the system SHALL select among soft-pass configurations whose annualized return is within 0.50 percentage points of the maximum soft-pass return, preferring the lowest `pending_cash_days`. When returns are otherwise within that edge, existing stock sub-split risk-budget preference still applies. Bond-variant-only differences MUST NOT displace a lower-pending peer inside the band.

#### Scenario: Near-max return picks lower pending

- **WHEN** soft-pass A returns within 0.50pp of the max soft-pass return with pending-cash days 645
- **AND** soft-pass B returns within 0.50pp of that max with pending-cash days 607
- **AND** both share the same allocation family eligible for primary
- **THEN** `primary` is B

### Requirement: Max-return contrast slot

The `max_return_contrast` role MUST be the soft-pass with the highest annualized return in the same `allocation_name` as `primary` when that configuration differs from `primary`. If no distinct contrast exists, the role MAY be omitted and the omission MUST be recorded in the shortlist artifact.

#### Scenario: Contrast shows peak vs primary

- **WHEN** `primary` is a lower-pending member of allocation `30-20-25-25`
- **AND** another `30-20-25-25` soft-pass has a higher annualized return
- **THEN** `max_return_contrast` is that higher-return configuration
- **AND** the shortlist pros/cons state the return delta and pending-cash delta

### Requirement: Forced step-down slot

The `step_down` role MUST select a soft-pass with allocation `25-25-25-25` when any such soft-pass exists, preferring the same stock sub-split as `primary` when available, then lower `pending_cash_days`, then higher annualized return. The shortlist MUST present step-down as an explicit trade of lower expected return for lower QDII pending friction relative to `primary`.

#### Scenario: Step-down filled from 25-25 family

- **WHEN** soft-passes include at least one `25-25-25-25` configuration
- **AND** `primary` uses stock sub-split `40-60`
- **THEN** `step_down` is a `25-25-25-25` soft-pass
- **AND** prefers `40-60` over other splits when both exist
- **AND** the artifact describes the return vs pending tradeoff versus `primary`

#### Scenario: No 25-25 soft-pass

- **WHEN** no `25-25-25-25` soft-pass exists
- **THEN** the shortlist records `step_down` as unavailable or applies a documented fallback
- **AND** still emits `primary` when possible

### Requirement: User pick from shortlist then sign-off lock

The system SHALL allow the user to select a shortlist `config_id` (or another passing configuration from the same run) and activate a lock only when that configuration becomes `lockable`, including via human sign-off that acknowledges all material `needs_review` items. If the selected configuration lacks a full artifact bundle, the system MUST run single-configuration validation before lock activation.

#### Scenario: Pick primary with sign-off

- **WHEN** the shortlist includes `primary` config P that is not naturally `lockable`
- **AND** the user selects P with a complete human sign-off
- **THEN** P becomes `lockable`
- **AND** the active strategy lock references P and the run directory

#### Scenario: Pick without sign-off blocked

- **WHEN** the user selects a shortlist configuration with open material reviews
- **AND** no human sign-off is provided
- **THEN** the system does not activate the strategy lock
