## ADDED Requirements

### Requirement: Lock integrity fields in artifacts

The artifact bundle and strategy-lock markdown MUST record `validation.passed`, `lockable`, material `needs_review` items, optional human sign-off (reviewer, timestamp, rationale, acknowledged items), CPI assumption used for historical real metrics, and stress mechanism labels where applicable.

#### Scenario: Bundle exposes lockable and sign-off

- **WHEN** a configuration is promoted to active lock with human sign-off
- **THEN** the artifact bundle includes `lockable: true` and the sign-off payload
- **AND** strategy-lock.md includes matching Sign-off and Assumptions sections

#### Scenario: Soft-pass without lock omits active lock stamp

- **WHEN** a configuration is `validation.passed` but not `lockable`
- **THEN** artifacts may still store the validation result for inspection
- **AND** MUST NOT mark the configuration as the active strategy lock
