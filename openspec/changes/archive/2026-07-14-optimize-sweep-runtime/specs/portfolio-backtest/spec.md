## ADDED Requirements

### Requirement: Reusable simulation execution within a sweep
The system SHALL reuse simulation results within a single sweep run when the simulation inputs and execution options are equivalent. The reuse key SHALL distinguish strategy configuration, rebalance mode, stress variant, price matrix identity, backup price inputs, and any simulation options that can affect results.

#### Scenario: Equivalent baseline simulation reused
- **WHEN** the sweep requests the same baseline simulation more than once for an equivalent configuration and data set
- **THEN** the later request reuses the previously computed result
- **AND** the returned portfolio path and simulation metrics are identical to a fresh simulation

#### Scenario: Incompatible simulation not reused
- **WHEN** the sweep requests a simulation with a different configuration, rebalance mode, stress variant, price matrix, or backup price input
- **THEN** the system treats it as a distinct simulation request
- **AND** no cached result from the incompatible request is used

### Requirement: Deferrable no-rebalance premium computation
The system SHALL allow broad sweep screening to defer the no-rebalance simulation used to calculate rebalance premium. When deferred, the system SHALL either mark the premium as unavailable for screening or compute it later for shortlisted and final-report configurations according to the selected runtime mode.

#### Scenario: Broad screening skips no-rebalance simulation
- **WHEN** the sweep runs in a mode that defers rebalance premium
- **THEN** each broad-screening candidate avoids the no-rebalance simulation
- **AND** validation logic does not depend on an exact rebalance premium unless it has been computed

#### Scenario: Final report includes exact rebalance premium
- **WHEN** a strategy is selected for final lock reporting
- **THEN** the system computes the no-rebalance simulation if it was previously deferred
- **AND** the final metrics include an exact rebalance premium
