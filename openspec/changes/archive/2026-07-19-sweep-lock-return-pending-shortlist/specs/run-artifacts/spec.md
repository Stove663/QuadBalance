## ADDED Requirements

### Requirement: Lock shortlist artifact

When the lock-candidate shortlist path runs after a sweep, the run output directory MUST include a machine-readable shortlist artifact (JSON with `schema_version`) and a human-readable markdown companion summarizing each role’s `config_id`, key metrics, material review differential, and pros/cons. These artifacts are additive and MUST NOT replace `sweep_results.csv`.

#### Scenario: Shortlist files written without active lock

- **WHEN** a sweep completes with zero natural `lockable` configurations and builds a shortlist
- **THEN** `lock-shortlist.json` (or equivalent) and `lock-shortlist.md` exist under the output directory
- **AND** each listed candidate includes `lockable: false` until a later sign-off lock
- **AND** `sweep_results.csv` remains present
