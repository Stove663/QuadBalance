## ADDED Requirements

### Requirement: Risk-budget preference in lock ranking for stock sub-split

When selecting a locked configuration among otherwise comparable candidates, lock ranking MUST apply a stocks sub-split risk-budget preference: prefer domestic-heavier `60-40` over `40-60` when annualized return advantage of the overseas-heavier split is less than 0.50 percentage points, OR when the overseas-heavier split introduces additional material cross-border `needs_review` findings not present on `60-40`. The preference MUST be documented in the strategy lock selection ranking keys. Sweep MUST continue to evaluate `60-40`, `50-50`, and `40-60`.

#### Scenario: Small return edge does not win on 40-60

- **WHEN** a `40-60` candidate annualized return exceeds an otherwise similar `60-40` candidate by less than 0.50 percentage points
- **THEN** lock selection prefers the `60-40` candidate
- **AND** the ranking keys document the risk-budget preference

#### Scenario: Extra CB reviews demote 40-60

- **WHEN** `40-60` has material cross-border reviews and `60-40` does not
- **AND** return rankings are otherwise close
- **THEN** lock selection prefers `60-40`
