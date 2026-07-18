# Strategy Validation Spec Update

## ADDED Requirements

### Requirement: staged validation sweep
The validation sweep SHALL support a staged execution model in which candidates are first screened using a low-cost pass and only candidates that satisfy the screening gate proceed to expensive validation steps.

#### Scenario: candidate fails fast screening
- **WHEN** a candidate fails the screening gate on core return or drawdown criteria
- **THEN** the sweep SHALL stop evaluating expensive stress and long-term analyses for that candidate
- **AND** the candidate SHALL be marked as rejected with the applicable failure reasons

#### Scenario: candidate passes screening
- **WHEN** a candidate satisfies the screening gate
- **THEN** the sweep SHALL evaluate the remaining deep validation checks for that candidate
- **AND** the final acceptance decision SHALL use the full validation result

### Requirement: screening gate thresholds
The screening gate SHALL be defined using fast-to-compute thresholds derived from core metrics.

#### Scenario: minimum screening conditions
- **WHEN** a candidate is screened
- **THEN** the screening gate SHALL evaluate at minimum real annualized return, max drawdown, and real terminal wealth
- **AND** candidates failing any of those thresholds SHALL not proceed to deep validation

### Requirement: reusable precomputed intermediates
The sweep SHALL reuse precomputed market and benchmark intermediates across candidates within a single run.

#### Scenario: multiple candidates share the same data slice
- **WHEN** multiple candidates use the same market history and benchmark series
- **THEN** the implementation SHALL compute invariant series once and reuse them for candidate evaluation
- **AND** repeated candidate evaluation SHALL NOT re-fetch or re-transform the same data unnecessarily

### Requirement: ranked deep validation subset
The sweep SHALL support ranking candidates by a lightweight score before running deep validation, so that the most promising configurations are validated first.

#### Scenario: many candidates remain after screening
- **WHEN** more candidates pass screening than are practical to fully validate within a reasonable time budget
- **THEN** the sweep SHALL prioritize deep validation for higher-ranked candidates first
- **AND** the ranking SHALL be derived from fast-to-compute metrics only

### Requirement: deep validation budget
The sweep SHALL support a configurable budget for deep validation when the screened candidate set is large.

#### Scenario: screened candidate set exceeds budget
- **WHEN** the number of screened candidates exceeds the deep validation budget
- **THEN** the sweep SHALL validate only the top-ranked candidates within the budget first
- **AND** the remaining candidates SHALL be deferred without changing the final selection rule for the validated set

### Requirement: deterministic final lock selection
The optimization changes SHALL NOT alter which configuration is selected as the final lock when the same set of candidates reaches deep validation.

#### Scenario: two runs over the same data
- **WHEN** the sweep runs twice over the same inputs
- **THEN** the final locked configuration and acceptance output SHALL remain deterministic
- **AND** the ordering of deep validation execution SHALL NOT affect the final selection
