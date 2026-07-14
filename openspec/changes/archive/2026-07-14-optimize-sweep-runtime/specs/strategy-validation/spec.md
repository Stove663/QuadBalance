## ADDED Requirements

### Requirement: Staged sweep validation
The system SHALL support staged sweep validation that separates broad candidate screening from final exact validation. Broad screening SHALL evaluate baseline metrics and fast stress for all candidates, while exact full stress SHALL run only for shortlisted candidates and final lock candidates by default.

#### Scenario: Candidate screened with fast validation
- **WHEN** the sweep evaluates all generated candidate configurations in staged mode
- **THEN** each candidate is evaluated with baseline simulation, performance metrics, suitability classification, and fast stress scenarios
- **AND** exact S4, S5, and S7 full-stress simulations are not required for candidates that are not shortlisted

#### Scenario: Shortlisted candidate receives exact full stress
- **WHEN** a candidate is shortlisted after broad screening
- **THEN** the system runs exact full stress validation for that candidate unless the selected mode explicitly allows approximate stress
- **AND** the pass/fail status used for final lock selection reflects the full-stress result

#### Scenario: Final lock uses exact validation by default
- **WHEN** a strategy-lock document or final run artifact is generated
- **THEN** the selected configuration has exact full-stress validation results by default
- **AND** the artifact identifies any non-default runtime or stress mode used during screening

### Requirement: S4 window-scoped evaluation mode
The system SHALL provide an explicit S4 evaluation mode that can choose between full-history exact path simulation and window-scoped path simulation. The selected mode SHALL be recorded with the S4 result.

#### Scenario: Full-history S4 preserves existing semantics
- **WHEN** S4 runs in full-history mode
- **THEN** the system applies the prolonged low-rate bond cap over the selected window within the full price history
- **AND** runs a full simulation before calculating the window cumulative return and pass/fail result

#### Scenario: Window-scoped S4 avoids full-history simulation
- **WHEN** S4 runs in window-scoped mode
- **THEN** the system evaluates only the selected S4 window price data
- **AND** calculates cumulative return, worst-year return, annualized window return, and pass/fail result from that window-scoped simulation
- **AND** the result indicates that window-scoped semantics were used

### Requirement: Approximate exploratory S5 and S7 stress
The system SHALL support an approximate stress mode for exploratory sweep screening. Approximate S5 and S7 stress SHALL estimate QDII premium and low-quota impact from existing simulation outputs without requiring full stress reruns, while exact stress SHALL remain the default for final validation.

#### Scenario: Approximate S5 avoids rerun
- **WHEN** exploratory stress mode is approximate
- **THEN** S5 QDII premium impact is estimated from existing portfolio exposure or QDII metrics
- **AND** the system does not rerun the full simulation solely for S5 during broad screening

#### Scenario: Approximate S7 avoids rerun
- **WHEN** exploratory stress mode is approximate
- **THEN** S7 low-quota impact is estimated from existing QDII fill, weight-gap, pending-cash, or related execution metrics
- **AND** the system does not rerun the full simulation solely for S7 during broad screening

#### Scenario: Exact final stress overrides exploratory approximation
- **WHEN** a candidate is selected for final lock validation
- **THEN** exact S5 and S7 stress simulations are run by default even if approximate stress was used during broad screening
- **AND** final validation pass/fail uses the exact stress results
