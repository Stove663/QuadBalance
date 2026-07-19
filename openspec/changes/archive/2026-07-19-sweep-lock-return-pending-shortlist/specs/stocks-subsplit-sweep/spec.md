## ADDED Requirements

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
