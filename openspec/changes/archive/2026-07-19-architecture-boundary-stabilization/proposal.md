## Why

The project has already grown into a strategy research and governance platform, but its modules still risk drifting across boundaries as validation, stress testing, reporting, and UI workflows expand. This change formalizes the architecture so the system remains predictable, auditable, and easier to evolve without duplicating business rules.

## What Changes

- Establish clear boundaries between domain models, calculation engines, orchestration flows, and presentation layers.
- Standardize run artifacts so CLI, UI, sweep, and lock-generation workflows produce the same traceable experiment record.
- Reduce duplication in validation, metrics, stress handling, and reporting logic by centralizing shared concepts.
- Make strategy validation and lock generation more deterministic and easier to audit across repeated runs.
- Improve module responsibilities so future features can be added without coupling UI or storage concerns to core strategy logic.
- Establish a single source of truth for shared calculations and status interpretation.
- Define canonical data contracts for strategy inputs, simulation results, validation results, and artifact manifests.
- Enforce a hard boundary so UI and presentation layers do not implement business rules or decision logic.

## Capabilities

### New Capabilities
- `architecture-boundary-stabilization`: defines the system behavior for stable module boundaries, shared run artifacts, and deterministic orchestration across validation workflows.

### Modified Capabilities

## Impact

Affected areas include the core `src/quadbalance/` modules, run artifact generation, validation and reporting workflows, CLI/UI orchestration, and the OpenSpec-driven change process for future feature work.
