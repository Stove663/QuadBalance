## ADDED Requirements

### Requirement: stress-test worker isolation
The system SHALL execute stress-test evaluation without relying on shared mutable state between worker tasks.

#### Scenario: independent stress scenarios remain isolated
- **WHEN** stress scenarios are evaluated in parallel or in separate workers
- **THEN** each scenario SHALL compute from its own inputs and SHALL NOT depend on mutable state written by another worker task

#### Scenario: read-only shared inputs are allowed
- **WHEN** multiple stress tasks use the same historical price data or configuration snapshots
- **THEN** those inputs SHALL be treated as read-only and may be reused safely across workers
