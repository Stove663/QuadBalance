## ADDED Requirements

### Requirement: Review-required findings do not fail acceptance

Acceptance evaluation SHALL distinguish hard failures from review-required findings. A candidate MUST NOT fail `validation.passed` solely because a short-horizon stress, path stress, behavior stress, cross-border stress, or product-risk result is classified `review-required`. Those findings MUST be recorded on a dedicated `needs_review` list (or equivalent) and MUST appear in sweep output and the strategy lock document. A candidate MUST fail when any such result is classified `fail` or `thesis-broken`, subject to the same primary metrics gates (drawdown, worst year, NAV recovery, return vs cash and 60/40).

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

### Requirement: Outcome-based cross-border stress classification

Cross-border stress classification SHALL be based on measured portfolio outcomes for the candidate configuration. Scenario-definition parameters that are fixed for a scenario (including liquidity impairment months and capital mobility constraint months) MAY annotate reasons and MAY contribute to a `review-required` classification, but MUST NOT alone force `thesis-broken`. `thesis-broken` MUST require at least one outcome breach such as portfolio return below the severe return threshold or frozen external-asset weight at or above the severe frozen-weight threshold.

#### Scenario: CB3 is not automatically thesis-broken

- **WHEN** CB3 is evaluated for a configuration whose portfolio return is above the severe return threshold
- **AND** frozen external-asset weight is below the severe frozen-weight threshold
- **THEN** CB3 is classified `review-required` or `normal`, not `thesis-broken`
- **AND** prolonged impairment months may still be listed in reasons

#### Scenario: Severe frozen weight still thesis-broken

- **WHEN** a cross-border scenario yields frozen external-asset weight at or above the severe frozen-weight threshold
- **THEN** the scenario is classified `thesis-broken`
- **AND** acceptance marks the configuration failed when that result is included in evaluation

## MODIFIED Requirements

### Requirement: Acceptance criteria

A candidate configuration SHALL pass validation and become eligible for strategy lock only when ALL of the following are met on the primary backtest period:

1. Maximum drawdown ≤ 25%
2. No single calendar year portfolio return below -20%
3. Hard stress gates: no short-horizon, path, behavior, cross-border, or product-risk result classified `fail` or `thesis-broken` (including S1–S7 portfolio-vs-worst-quadrant checks where applicable). Results classified `review-required` do not fail this gate; they MUST be recorded as `needs_review`
4. Annualized return exceeds cash-only benchmark (511880) by at least 2%
5. Annualized return is not more than 2% below the 60/40 benchmark, OR max drawdown is at least 5% lower than the 60/40 benchmark

NAV recovery constraints that the implementation already applies as Criterion 3 hard gates remain hard failures when breached.

#### Scenario: Configuration passes all criteria

- **WHEN** a candidate achieves 10% annualized return, 18% max drawdown, worst year -12%
- **AND** no stress-family result is `fail` or `thesis-broken`
- **AND** return exceeds cash benchmark by 3%
- **AND** max drawdown is 8% lower than 60/40 benchmark
- **THEN** the configuration is marked "validation passed"
- **AND** any `review-required` findings appear only under `needs_review`

#### Scenario: Configuration fails drawdown criterion

- **WHEN** a candidate achieves 12% annualized return but 30% max drawdown
- **THEN** the configuration is marked "validation failed"
- **AND** the failure reason cites criterion 1 (max drawdown > 25%)

#### Scenario: Configuration fails only on thesis-broken extended stress

- **WHEN** a candidate meets metrics gates 1, 2, 4, and 5
- **AND** a cross-border or extended stress result is `thesis-broken`
- **THEN** the configuration is marked "validation failed"
- **AND** the failure reason cites that stress result
