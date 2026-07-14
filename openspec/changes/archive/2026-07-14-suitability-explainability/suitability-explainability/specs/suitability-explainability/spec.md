# Specification: Optimize Sweep and Stress-Test Execution

## ADDED Requirements

### Requirement: Two-Phase Sweep Evaluation
The system MUST evaluate sweep configurations in two phases:
1. a fast phase that runs the primary simulation and inexpensive validation checks
2. a full phase that runs expensive stress tests only for configurations that remain viable after the fast phase

#### Acceptance Criteria
- The fast phase MUST compute the main simulation result for each configuration.
- The fast phase MUST compute the metrics required for initial acceptance filtering.
- The full phase MUST only run for configurations that satisfy the fast-phase gate.
- The final output MUST remain deterministic for the same input data and configuration set.

### Requirement: Reuse Shared Intermediate Results
The system MUST reuse intermediate results that are derived once per configuration and consumed by multiple downstream steps.

#### Acceptance Criteria
- The system MUST avoid recomputing the no-rebalance comparison when the same configuration data is already available.
- The system MUST reuse the primary simulation output for metrics, validation, and any stress-test logic that can consume it directly.
- The system MUST derive risk-free and benchmark values once per sweep run, not once per configuration.

### Requirement: Fast Stress-Test Gate
The system MUST provide a fast stress-test gate that can reject configurations before expensive scenario replay is performed.

#### Acceptance Criteria
- The fast gate MUST be based on already computed results or lightweight derivations from them.
- Configurations that fail the fast gate MUST NOT run full stress scenarios.
- The full stress suite MUST remain available for configurations that pass the gate.

### Requirement: Parallel Configuration Execution
The system SHOULD execute independent configurations in parallel to reduce wall-clock runtime.

#### Acceptance Criteria
- Each configuration MUST be runnable as an independent work unit.
- Parallel execution MUST not alter the final chosen configuration for the same input set.
- Result aggregation MUST preserve the same report schema as the current implementation.

### Requirement: Stable Candidate Selection
The system MUST preserve the current deterministic configuration ranking semantics when selecting the locked candidate.

#### Acceptance Criteria
- The ranking keys MUST remain stable and ordered consistently.
- Ties MUST continue to resolve deterministically.
- The selected configuration MUST not depend on execution order.

### Requirement: Preserve External Artifacts
The system MUST continue producing the existing sweep and report artifacts.

#### Acceptance Criteria
- The sweep results CSV MUST still be written.
- The strategy lock document MUST still be produced for accepted candidates.
- Existing downstream artifact generation MUST remain available.

## Operational Notes

- The optimization is intended to reduce runtime without changing portfolio logic.
- Any caching introduced by this change MUST be scoped to a single run unless explicitly persisted by existing infrastructure.
- Full stress tests remain authoritative for final acceptance; the fast phase is only a filter.
