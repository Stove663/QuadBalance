## ADDED Requirements

### Requirement: Stocks quadrant sub-split sweep
The system SHALL support a sweepable Stocks quadrant domestic/QDII sub-split dimension during validation runs. The sweep SHALL include the documented variants 60/40, 50/50, and 40/60, and each candidate configuration SHALL record the selected split explicitly in configuration identity and outputs.

#### Scenario: Default split remains baseline
- **WHEN** the engine generates validation candidates without an explicit override
- **THEN** the Stocks quadrant uses the 60/40 domestic/QDII split
- **AND** the selected split is recorded in the run output

#### Scenario: Alternate split included in sweep
- **WHEN** a validation sweep is generated
- **THEN** candidate configurations include 50/50 and 40/60 Stocks quadrant split variants
- **AND** each variant is distinguishable by configuration identity
