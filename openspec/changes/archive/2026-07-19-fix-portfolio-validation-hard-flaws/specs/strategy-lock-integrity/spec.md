## ADDED Requirements

### Requirement: Lockable distinct from validation passed

The system SHALL distinguish `validation.passed` from `lockable`. A configuration MAY pass validation when primary metrics gates succeed and no stress-family result is `fail` or `thesis-broken`, even if `needs_review` is non-empty. A configuration MUST be `lockable` only when `validation.passed` is true AND either material `needs_review` is empty OR a complete human sign-off artifact is recorded. Strategy-lock document generation and active lock promotion MUST require `lockable`.

#### Scenario: Passed with open material reviews is not lockable

- **WHEN** a configuration meets primary metrics gates
- **AND** cross-border or path stress results are `review-required`
- **AND** no human sign-off is recorded
- **THEN** `validation.passed` MAY be true
- **AND** `lockable` is false
- **AND** strategy-lock.md MUST NOT be written as the active lock

#### Scenario: Sign-off unlocks lockable with open reviews

- **WHEN** a configuration is `validation.passed` with material `needs_review` items
- **AND** a human sign-off records reviewer identity, timestamp, rationale, and the exact open item list
- **THEN** the configuration is `lockable`
- **AND** strategy-lock.md includes the sign-off section verbatim

### Requirement: Material needs_review catalog

The system SHALL treat the following as material lock blockers when classified `review-required` or worse, unless human sign-off is present: any cross-border stress result; any dynamic path stress result; short-horizon scenarios S14, S15, and S20; product-level worst classification `review-required` or worse; unrecovered maximum drawdown at sample end; and long-term `seq_inflation` thesis-broken (per long-term-macro-regime-stress). Non-material reviews MAY remain informational without blocking `lockable`.

#### Scenario: CB review is material

- **WHEN** CB2 is classified `review-required`
- **THEN** it appears in material `needs_review`
- **AND** `lockable` is false without sign-off

#### Scenario: Informational review does not block alone

- **WHEN** the only `needs_review` items are explicitly marked non-material
- **AND** primary gates pass
- **THEN** `lockable` is true without sign-off

### Requirement: Risk Overview severity matches Risk Map

The Risk Overview panel SHALL derive red/yellow/green layer status from the same severity rules used by the Risk Map. Overview MUST NOT claim zero red items or “未见明确红色风险” when any Risk Map layer is red.

#### Scenario: Cross-border red appears in Overview

- **WHEN** Risk Map ranks 跨境访问与结算约束 as red
- **THEN** Risk Overview red item count is at least 1
- **AND** the one-page summary does not state that no clear red risk exists

### Requirement: CPI assumption disclosure

Historical real-return metrics that use a constant inflation rate MUST record that rate in strategy-lock.md and metrics artifacts. The document MUST state that long-term regime stresses may use different CPI paths.

#### Scenario: Lock documents CPI rate

- **WHEN** strategy-lock.md is generated with constant inflation_annual = 0.03
- **THEN** Core Metrics or an Assumptions section states CPI assumption 3.0% annual
- **AND** notes that LT scenarios may use different CPI paths

### Requirement: Stress mechanism labeling

Each short-horizon and cross-border stress row in strategy-lock.md MUST label whether the result is a closed-form / formula shock or a full portfolio path simulation.

#### Scenario: Formula stress labeled

- **WHEN** S14 is evaluated via weighted quadrant haircuts without a full `simulate()` path
- **THEN** the stress table notes column or Notes field identifies it as formula/closed-form
