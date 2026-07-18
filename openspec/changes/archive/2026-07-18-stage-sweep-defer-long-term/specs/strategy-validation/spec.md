## ADDED Requirements

### Requirement: Staged sweep evaluation pipeline

The backtest engine MUST evaluate sweep candidates in stages so that more expensive analyses run only after cheaper gates succeed for that candidate.

Required stage order for each sweep candidate:

1. Historical portfolio simulation and core performance metrics.
2. Short-horizon / execution stress evaluation (S1–S21 family and related path tests used by acceptance).
3. Acceptance evaluation used for sweep pass/fail and lock ranking.

Long-term macro regime stress (LT1–LT3) MUST NOT run in the per-candidate deep path by default. It MUST run only after a configuration is selected for strategy lock, and only if that configuration has already completed primary validation including short-horizon stress.

Each sweep result row MUST record a validation stage that distinguishes at least screened-out candidates from deep-validated candidates.

#### Scenario: Failed metric screen skips stress and long-term

- **WHEN** a candidate fails the early metric screen
- **THEN** the engine does not run short-horizon stress for that candidate
- **AND** the engine does not run LT1–LT3 for that candidate
- **AND** the sweep row records a screened-out validation stage

#### Scenario: Deep-validated candidates skip per-candidate long-term

- **WHEN** a candidate passes the early metric screen and completes short-horizon stress plus acceptance evaluation
- **THEN** the sweep row is marked deep-validated
- **AND** LT1–LT3 are not executed as part of that candidate's worker evaluation by default

#### Scenario: Locked configuration receives long-term after stress

- **WHEN** at least one configuration passes primary validation and is selected for strategy lock
- **THEN** the engine runs LT1–LT3 for that locked configuration after short-horizon stress validation for it has completed
- **AND** the long-term results are attached before strategy-lock document generation

## MODIFIED Requirements

### Requirement: Long-term macro regime stress in strategy validation

When a configuration is selected for strategy lock, the validation suite SHALL run long-term macro regime stress scenarios for the locked configuration after primary sweep validation and short-horizon stress validation complete.

Long-term macro regime stress results MUST be reported separately from S1-S21 short-horizon and execution-friction stress tests. Long-term regime results MUST NOT silently change the selected allocation, but they MUST be included in the strategy boundary and governance evidence for the locked strategy.

The sweep MUST NOT run LT1–LT3 for every deep-validated candidate by default. Long-term scenarios are a lock-path governance analysis, not a per-candidate ranking input.

#### Scenario: Long-term regime stress runs for locked configuration

- **WHEN** a configuration passes primary validation and is selected for strategy lock
- **THEN** the validation suite runs LT1, LT2, and LT3 for that locked configuration
- **AND** the results are available to the strategy lock document generator

#### Scenario: Long-term regime stress does not affect sweep ranking

- **WHEN** multiple configurations pass primary validation
- **THEN** long-term macro regime stress is not run for every sweep candidate by default
- **AND** the selected locked allocation is not silently changed based on LT1-LT3 results

#### Scenario: Long-term is deferred until lock selection

- **WHEN** the parameter sweep evaluates the full candidate grid
- **THEN** worker evaluation for non-locked candidates omits LT1–LT3 by default
- **AND** LT1–LT3 execute at most once for the selected locked configuration in a normal sweep run
