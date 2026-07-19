## ADDED Requirements

### Requirement: Alignment callers exclude QDII backups

Sweep and single-run market-data loading MUST NOT pass QDII backup symbols into the alignment price matrix. `collect_required_symbols` (and equivalents) MUST return primary/alignment symbols only. Backup symbols MUST be supplied solely through the backup price loading path. The engine MUST assert that alignment matrix columns do not intersect `QDII_BACKUP_SYMBOLS`.

#### Scenario: Sweep alignment start not truncated by 006075

- **WHEN** a full validation sweep loads market data for configurations with QDII quota enabled
- **THEN** the alignment price matrix columns exclude 050025 and 006075
- **AND** locked configuration `effective_start` is on or before 2013-08-01
- **AND** `effective_start` is not 2018-06-08

#### Scenario: Assertion fires on backup contamination

- **WHEN** a caller attempts to include 006075 in alignment symbols
- **THEN** loading fails fast with an explicit error naming the forbidden backup symbol

### Requirement: QDII quality gates beyond fill rate

Validation and lock eligibility MUST evaluate QDII execution quality using fill rate together with average QDII weight gap, pending-cash day count, and maximum post-rebalance deviation. A 100% fill rate MUST NOT clear material review when pending-cash days exceed 252 or average QDII weight remains more than 2 percentage points below target for at least 12 months, or when maximum post-rebalance deviation exceeds the configured rebalance threshold.

#### Scenario: Perfect fill with chronic pending is material review

- **WHEN** QDII fill rate is 100%
- **AND** pending-cash days exceed 252
- **THEN** validation records a material `needs_review` finding citing pending-cash duration
- **AND** fill rate alone does not suppress that finding

#### Scenario: Weight gap sustained 12 months is material review

- **WHEN** average actual QDII weight stays more than 2 percentage points below target for at least 12 months
- **THEN** a material `needs_review` finding is recorded

### Requirement: Suitability uses measured QDII metrics

Profile suitability classification invoked from validation MUST receive measured QDII fill rate, average QDII weight gap, and available friction/recovery metrics from the simulation result. Hardcoded perfect-execution defaults (fill rate 1.0 and weight gap 0.0) MUST NOT be used when simulation metrics exist.

#### Scenario: Validation passes real fill rate

- **WHEN** simulation reports fill rate 0.85 and average weight gap -0.03
- **THEN** `classify_suitability` is called with those measured values
- **AND** not with 1.0 and 0.0

### Requirement: Behavior stress dual evaluation

Behavioral stress rules MUST be evaluated on the historical portfolio path and ALSO against deep-drawdown proxies from path stress and selected short-horizon stresses (at least P1 maximum drawdown and S14 portfolio return as a drawdown surrogate). Strategy-lock behavior reporting MUST show both historical and stress-fed results. Risk Overview MUST NOT mark the behavior layer green solely because historical maximum drawdown never reached rule triggers when stress-fed evaluation was skipped.

#### Scenario: Historical shallow MDD still runs stress-fed rules

- **WHEN** historical maximum drawdown is milder than -10%
- **AND** P1 maximum drawdown is at or beyond a behavior rule trigger
- **THEN** stress-fed behavior evaluation records a triggered or classified result for that rule
- **AND** the lock document distinguishes historical vs stress-fed columns

### Requirement: Unrecovered end-sample drawdown is material

When maximum drawdown has no recovery date by the sample end, validation MUST record a material `needs_review` finding regardless of whether the drawdown depth is above or below -10%. Depth MAY still affect hard-fail vs review wording for other Criterion 3 gates, but open unrecovered drawdown at lock time MUST block `lockable` without sign-off.

#### Scenario: Open drawdown at sample end blocks lockable

- **WHEN** max drawdown trough has no recovery before the last simulation date
- **THEN** material `needs_review` includes unrecovered drawdown
- **AND** `lockable` is false without human sign-off

### Requirement: Lock selection prefers lockable candidates

Deterministic final lock selection MUST prefer `lockable` candidates. Configurations that are `validation.passed` but not `lockable` MUST NOT become the active strategy lock unless an explicit human sign-off is supplied for that configuration during the lock step.

#### Scenario: Soft-pass candidate skipped for lock

- **WHEN** multiple candidates pass validation
- **AND** only one is `lockable` without sign-off
- **THEN** the locked configuration is that lockable candidate

## MODIFIED Requirements

### Requirement: Review-required findings do not fail acceptance

Acceptance evaluation SHALL distinguish hard failures from review-required findings. A candidate MUST NOT fail `validation.passed` solely because a short-horizon stress, path stress, behavior stress, cross-border stress, or product-risk result is classified `review-required`. Those findings MUST be recorded on a dedicated `needs_review` list (or equivalent) and MUST appear in sweep output and the strategy lock document. A candidate MUST fail when any such result is classified `fail` or `thesis-broken`, subject to the same primary metrics gates (drawdown, worst year, NAV recovery, return vs cash and 60/40). Material `needs_review` findings MUST block `lockable` unless human sign-off is recorded per strategy-lock-integrity.

#### Scenario: Review-required stress does not block pass

- **WHEN** a candidate meets primary metrics gates
- **AND** all stress / path / behavior / cross-border / product-risk results are either `normal` or `review-required`
- **AND** none are `fail` or `thesis-broken`
- **THEN** the configuration is marked validation passed
- **AND** each `review-required` finding is listed in `needs_review`
- **AND** `failure_reasons` does not include those review-required findings

#### Scenario: Thesis-broken stress still blocks pass

- **WHEN** a candidate meets primary metrics gates
- **AND** any stress / path / behavior / cross-border / product-risk result is classified `fail` or `thesis-broken`
- **THEN** the configuration is marked validation failed
- **AND** the failure reason cites that scenario or boundary

#### Scenario: Sweep CSV exposes needs_review

- **WHEN** a sweep row is written for a deep-validated configuration with review-required findings
- **THEN** the row includes a `needs_review` field listing those findings
- **AND** `validation_passed` may still be true when `failure_reasons` is empty

#### Scenario: Sweep CSV exposes lockable

- **WHEN** a sweep row is written for a deep-validated configuration
- **THEN** the row includes a `lockable` boolean
- **AND** `lockable` is false when material `needs_review` is non-empty and no sign-off is attached
