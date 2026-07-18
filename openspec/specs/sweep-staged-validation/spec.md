# sweep-staged-validation

## Purpose

Define staged and shortlist-based sweep validation so expensive exact evaluation runs only where needed.

## Requirements

### Requirement: shortlist-based exact evaluation
The system SHALL run exact stress tests and related expensive follow-up work only for shortlisted passing configurations.

#### Scenario: only shortlisted candidates get exact evaluation
- **WHEN** the sweep completes fast validation across the configuration space
- **THEN** it SHALL select only a small shortlist of passing candidates for exact stress testing

#### Scenario: locked configuration still receives full artifacts
- **WHEN** a configuration is selected as the lock candidate
- **THEN** the system SHALL generate the full stress outputs and run artifact generation for that candidate


### Requirement: staged validation flow
The system SHALL preserve a staged validation flow in which configurations are fast-screened before the most expensive stress tests are run.

#### Scenario: fast screen before exact stress
- **WHEN** the sweep evaluates a configuration
- **THEN** it SHALL first perform lightweight validation using the fast stress set
- **AND** it SHALL only run exact full stress tests after the configuration passes the fast validation gate

#### Scenario: rejected configurations skip exact stress
- **WHEN** a configuration fails fast validation
- **THEN** the system SHALL skip exact stress testing and expensive artifact generation for that configuration
