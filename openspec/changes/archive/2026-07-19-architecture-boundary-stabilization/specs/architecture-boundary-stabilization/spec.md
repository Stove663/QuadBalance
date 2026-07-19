## ADDED Requirements

### Requirement: Clear architectural boundaries
The system MUST separate domain concepts, calculation logic, orchestration workflows, and presentation concerns so that core strategy behavior does not depend on UI, filesystem, or database implementation details.

#### Scenario: Domain logic remains isolated
- **WHEN** validation or backtest logic is executed
- **THEN** the core strategy rules are evaluated without requiring UI-specific or reporting-specific code paths

#### Scenario: Presentation code does not define rules
- **WHEN** reports or UI views are generated
- **THEN** they consume existing strategy results and MUST NOT become the source of truth for business rules

### Requirement: Shared experiment run model
The system MUST represent every backtest, sweep, validation, or lock-generation execution as a structured run with stable metadata, input configuration, outputs, and artifact locations.

#### Scenario: CLI and UI use the same run model
- **WHEN** a run is launched from CLI or UI
- **THEN** the resulting run record contains the same core metadata fields
- **AND** the same output structure is produced for later inspection

#### Scenario: Run outputs are traceable
- **WHEN** a run completes
- **THEN** the output includes identifiers and paths sufficient to reproduce and audit the execution

### Requirement: Deterministic orchestration
The system MUST make validation and lock-selection flows deterministic for the same inputs, including ordering of candidate evaluation, acceptance outcomes, and final lock selection.

#### Scenario: Same inputs produce same selection
- **WHEN** the same candidate set, data slice, and validation rules are executed twice
- **THEN** the selected locked configuration is the same in both runs

#### Scenario: Evaluation order does not alter outcome
- **WHEN** candidate evaluation is parallelized or staged
- **THEN** the final acceptance result remains unchanged for identical inputs

### Requirement: Centralized shared strategy metadata
The system MUST define common structures for strategy inputs, validation results, stress outcomes, and reporting summaries so that duplicate implementations are avoided across modules.

#### Scenario: Validation and reporting share one result schema
- **WHEN** a strategy passes or fails validation
- **THEN** downstream reporting consumes the same canonical result object rather than recomputing its own interpretation

#### Scenario: Metrics remain consistent across modules
- **WHEN** a metric is displayed in multiple outputs
- **THEN** it is derived from the same shared calculation source and uses the same definition

### Requirement: Single source of truth for shared calculations
The system MUST centralize shared metric calculations, status interpretation, and artifact shaping so that the same business rule is not implemented in multiple modules with different outcomes.

#### Scenario: Shared calculation is reused
- **WHEN** a metric or validation status is needed by more than one workflow
- **THEN** the workflow consumes the shared implementation rather than defining a local alternative

#### Scenario: Conflicting interpretations are prevented
- **WHEN** validation and reporting both need to classify the same result
- **THEN** they MUST use the same canonical interpretation rules and produce the same classification

### Requirement: Canonical data contracts
The system MUST define explicit schemas for strategy inputs, simulation results, validation results, and artifact manifests so that core data structures are stable and inspectable.

#### Scenario: Inputs and outputs use shared schemas
- **WHEN** a run is created or completed
- **THEN** its input and output payloads conform to the canonical data contract for that workflow

#### Scenario: Artifact manifests are structured
- **WHEN** an artifact is generated
- **THEN** it includes stable fields for type, source run, and location

### Requirement: UI and presentation remain orchestration only
The UI and presentation layers MUST orchestrate user flows and render existing outputs, but MUST NOT own validation rules, business decisions, or acceptance criteria.

#### Scenario: UI consumes core results
- **WHEN** a user triggers a validation or reporting action from the UI
- **THEN** the UI calls the core workflow and displays the returned result without re-implementing the decision logic

#### Scenario: Presentation cannot redefine outcomes
- **WHEN** a report view is generated
- **THEN** it renders core results only and MUST NOT alter validation, lockability, or suitability outcomes

### Requirement: Unified artifact generation
The system MUST persist standardized artifacts for runs, validation summaries, and strategy lock documents so that CLI, UI, and batch workflows all produce auditable outputs.

#### Scenario: Artifact schema is consistent
- **WHEN** different workflows emit run artifacts
- **THEN** they use the same structural conventions for identifiers, summaries, and references

#### Scenario: Lock document references run artifacts
- **WHEN** a strategy lock document is generated
- **THEN** it points to the run artifacts used to support the decision

### Requirement: Stable extension points for future features
The architecture MUST allow new stress scenarios, metrics, validation gates, and presentation views to be added without requiring unrelated modules to be modified.

#### Scenario: New scenario fits existing boundaries
- **WHEN** a new stress scenario is introduced
- **THEN** it can be added through the stress/validation layer without changing UI implementation details

#### Scenario: New report view reuses core outputs
- **WHEN** a new report format is added
- **THEN** it consumes existing run and validation outputs rather than introducing a parallel data model
