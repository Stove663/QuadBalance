## ADDED Requirements

### Requirement: Measured execution friction inputs required

When simulation QDII metrics are available, suitability classification MUST consume those measured values for fill rate, average weight gap, and friction duration fields. Call sites MUST NOT substitute perfect-execution placeholders.

#### Scenario: Caution driven by measured weight gap

- **WHEN** measured average QDII weight gap is worse than -2 percentage points for at least 12 months
- **THEN** affected profile payloads include execution-friction reasons or warnings derived from that measurement
- **AND** the classification does not assume fill rate 100% cleared the friction

#### Scenario: Sequence risk passed through when available

- **WHEN** lifecycle sequence-risk results are available to validation
- **THEN** suitability classification receives the sequence-risk payload
- **AND** does not pass an empty mapping solely as a hardcoded default when results exist
