## ADDED Requirements

### Requirement: Shortlist does not imply lockable

Presenting a configuration on the lock-candidate shortlist MUST NOT set `lockable` to true and MUST NOT write an active strategy-lock document by itself. Shortlist rows that still carry material `needs_review` remain soft-pass until human sign-off (or clearance of material reviews) per the lockable gate.

#### Scenario: Shortlist row stays not lockable

- **WHEN** a soft-pass configuration appears as `primary` on the shortlist
- **AND** material cross-border or other material reviews remain open
- **AND** no human sign-off is recorded
- **THEN** `lockable` remains false
- **AND** strategy-lock.md MUST NOT be written as the active lock solely due to shortlist membership
