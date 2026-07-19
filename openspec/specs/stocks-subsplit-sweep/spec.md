# stocks-subsplit-sweep

## Purpose

Define Stocks quadrant domestic/QDII sub-split as a sweepable mechanical parameter.

## Requirements

### Requirement: Stocks quadrant sub-split sweep
The system SHALL support a sweepable Stocks quadrant domestic/QDII sub-split dimension during validation runs. The sweep SHALL include the documented variants 60/40, 50/50, and 40/60, and each candidate configuration SHALL record the selected split explicitly in configuration identity and outputs.

#### Scenario: Default split remains baseline
- **WHEN** the engine generates validation candidates without an explicit override
- **THEN** the Stocks quadrant uses the 60/40 domestic/QDII split
- **AND** the selected split is recorded in the run output

#### Scenario: Alternate split included in sweep
- **WHEN** a validation sweep is generated
- **THEN** candidate configurations include 50/50 and 40/60 Stocks quadrant split variants
- **AND** each variant is distinguishable by configuration identity

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

### Requirement: Same-return pending-cash preference in lock ranking

When ranking lock or shortlist candidates whose annualized returns differ by less than 0.50 percentage points, the system MUST prefer the candidate with lower QDII `pending_cash_days` after applying lockable-over-soft-pass preference. This pending preference MUST be documented in lock selection ranking keys alongside the stocks sub-split risk-budget preference. Sweep MUST continue to evaluate all configured stock sub-splits.

#### Scenario: Lower pending wins inside return edge

- **WHEN** two soft-pass candidates differ by less than 0.50pp annualized return
- **AND** candidate A has fewer pending-cash days than candidate B
- **THEN** lock/shortlist ranking prefers A
- **AND** ranking keys document the pending-cash preference

#### Scenario: Large return edge still wins

- **WHEN** candidate B exceeds candidate A by 0.50pp or more annualized return
- **THEN** ranking MAY prefer B despite higher pending-cash days
- **AND** shortlist contrast roles MAY still surface A separately when role rules require it

