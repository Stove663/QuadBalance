## ADDED Requirements

### Requirement: Sequence inflation thesis-broken vetoes lock

When any long-term scenario's inflation-escalating withdrawal sequence (`seq_inflation`) is classified `thesis-broken`, the system MUST record a material lock veto: the scenario classification MUST be at least `review-required`, the finding MUST appear in material `needs_review`, and the configuration MUST NOT be `lockable` without human sign-off that explicitly acknowledges the inflation-withdrawal failure.

#### Scenario: LT1 seq_inflation blocks lockable

- **WHEN** LT1 reports `seq_inflation: thesis-broken`
- **AND** no human sign-off acknowledges that finding
- **THEN** LT1 classification is not softer than `review-required`
- **AND** `lockable` is false

#### Scenario: Fixed 4% pass does not clear inflation veto

- **WHEN** the fixed nominal 4% withdrawal path does not deplete
- **AND** `seq_inflation` is `thesis-broken`
- **THEN** the inflation sequence veto still applies

## MODIFIED Requirements

### Requirement: Long-term regime governance classification

The validation suite SHALL classify each long-term macro regime result as `normal`, `review-required`, or `thesis-broken` using deterministic governance thresholds.

Default classifications MUST follow these rules unless explicitly overridden by future profile thresholds:

1. `normal` when real annualized return is non-negative, real terminal wealth is at or above initial real wealth, longest underwater duration does not exceed 5 years, no enabled withdrawal test depletes, and no sequence-risk profile is `thesis-broken`.
2. `review-required` when real annualized return is negative, real terminal wealth is below initial real wealth, longest underwater duration exceeds 5 years without meeting thesis-broken thresholds, or any sequence-risk profile is `thesis-broken` without meeting scenario-level thesis-broken thresholds.
3. `thesis-broken` when real terminal wealth loss exceeds 20%, longest underwater duration exceeds 10 years, worst rolling 10-year real return is below -10%, or a 4% real withdrawal path depletes.

Sequence-risk profile classifications MUST be retained in reporting even when they escalate the parent scenario only to `review-required`.

#### Scenario: Review-required long-term result

- **WHEN** LT1 has negative real annualized return but real terminal wealth loss is not worse than 20%
- **THEN** LT1 is classified as `review-required`
- **AND** the report states which threshold caused the classification

#### Scenario: Thesis-broken long-term result

- **WHEN** LT3 has real terminal wealth loss greater than 20%
- **THEN** LT3 is classified as `thesis-broken`
- **AND** the strategy lock document requires re-validation before relying on the allocation for that regime

#### Scenario: Seq inflation escalates scenario to review-required

- **WHEN** LT2 would otherwise be `normal` on real-return thresholds
- **AND** `seq_inflation` is `thesis-broken`
- **THEN** LT2 is classified at least `review-required`
- **AND** reasons cite the inflation-escalating withdrawal sequence
