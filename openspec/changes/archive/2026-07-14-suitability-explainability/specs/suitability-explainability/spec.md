## ADDED Requirements

### Requirement: Structured suitability explanation payload
The system MUST produce a structured suitability explanation payload for every investor profile classification. The payload SHALL include the classification, a list of human-readable reasons, a list of key drivers, a list of warnings, and governance notes.

#### Scenario: Suitability payload emitted for each profile
- **WHEN** a backtest or validation run completes
- **THEN** the system produces a suitability explanation payload for accumulation, balanced core, pre-retirement preservation, and retirement withdrawal
- **AND** each payload includes classification, reasons, drivers, warnings, and governance notes

#### Scenario: Payload remains machine-readable
- **WHEN** downstream consumers render the suitability result
- **THEN** they consume the structured payload rather than re-deriving the classification logic
- **AND** the payload can be serialized for reports, CLI output, and artifacts

### Requirement: Classification reasons are mandatory
Each suitability classification SHALL include at least one human-readable reason that explains the primary decision drivers. The reasons MUST be specific enough to identify whether the classification was driven by returns, drawdown, rolling real-return failures, underwater duration, execution friction, or lifecycle stress test outcomes.

#### Scenario: Reason attached to caution classification
- **WHEN** a profile is classified as `caution`
- **THEN** the explanation includes at least one reason describing the limiting factor
- **AND** the reason references the relevant metric or stress result

#### Scenario: Reason attached to unsuitable classification
- **WHEN** a profile is classified as `unsuitable`
- **THEN** the explanation includes at least one reason describing the failure boundary
- **AND** the reason identifies the failing profile constraint

### Requirement: Governance notes are separated from classification reasons
The system MUST keep governance notes separate from classification reasons. Governance notes SHALL describe review actions or policy implications, but MUST NOT redefine the suitability classification itself.

#### Scenario: Governance note does not alter the classification label
- **WHEN** a profile result includes a governance warning
- **THEN** the classification label remains unchanged
- **AND** the governance note is emitted separately from the reasons list

#### Scenario: Review-required guidance is explicit
- **WHEN** a result implies human review is needed
- **THEN** the payload includes governance notes that identify the review concern
- **AND** the notes do not instruct automatic allocation redesign

### Requirement: Suitability explanations reuse validation outputs
The explanation payload MUST be derived from existing validation outputs and SHALL NOT recompute portfolio metrics independently. The payload MUST consume the metrics already produced by backtest, stress test, lifecycle simulation, and execution-friction evaluation.

#### Scenario: Explanation derived from validation results
- **WHEN** validation metrics are available
- **THEN** the explanation payload uses those metrics as inputs
- **AND** it does not duplicate or independently recompute the underlying calculations

### Requirement: Profile-specific emphasis in explanation output
The explanation payload SHALL preserve a common structure across profiles while allowing profile-specific emphasis. Accumulation explanations SHOULD emphasize real growth and execution friction; balanced core explanations SHOULD emphasize volatility control and drawdown; pre-retirement explanations SHOULD emphasize recovery time and interruption resilience; retirement explanations SHOULD emphasize depletion risk and purchasing-power preservation.

#### Scenario: Profile emphasis differs by use case
- **WHEN** the system emits explanations for multiple profiles
- **THEN** the payload structure remains consistent
- **AND** the highlighted drivers differ according to the profile’s investment horizon and cashflow assumptions
