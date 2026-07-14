# Proposal: Optimize `/openspec-explore` Sweep and Stress-Test Execution

## Summary

This change optimizes the `/openspec-explore` execution path by reducing redundant simulation work, splitting stress tests into fast and full tiers, and enabling configuration-level parallelism. The goal is to preserve current report outputs while significantly reducing end-to-end runtime for full sweep execution.

## Problem

The current sweep flow spends most of its time in repeated, overlapping work:

- every candidate configuration runs a full simulation
- a no-rebalance simulation is run again for the same configuration
- stress testing may trigger additional full simulations for scenario variants
- all configurations are processed serially
- clearly failing configurations still pay the cost of full downstream evaluation

This makes `/openspec-explore` slow and expensive to run, especially when the number of candidate configurations grows.

## Goals

- Reduce total runtime of the sweep pipeline
- Reuse intermediate results wherever possible
- Avoid expensive stress tests for configurations that already fail obvious acceptance gates
- Preserve deterministic selection and report generation
- Keep existing outputs and report semantics stable

## Non-Goals

- Changing the underlying portfolio logic or acceptance thresholds
- Redesigning the simulation model itself
- Removing stress scenarios or weakening validation criteria
- Changing report file names or user-facing CLI behavior

## Proposed Approach

### 1. Split validation into fast and full phases

Introduce a two-stage evaluation flow:

- **Fast phase**: run the main simulation, derive metrics, and apply inexpensive acceptance checks
- **Full phase**: only for promising candidates, run the more expensive stress scenarios and lifecycle-sensitive checks

This allows the system to stop spending compute on configurations that are already clearly unsuitable.

### 2. Separate stress tests into reusable tiers

Refactor stress execution into:

- **Fast stress tests** that can be evaluated from already computed statistics, such as aggregated annual quadrant returns and existing daily value series
- **Full stress tests** that require additional simulation work, such as parameter perturbation scenarios and path-based tests

The fast tier acts as a gate before running the full tier.

### 3. Cache or reuse common intermediate results

Reuse outputs that are identical across downstream steps for a given configuration, including:

- main simulation result
- no-rebalance comparison result
- annual quadrant returns
- QDII execution statistics
- benchmark computations
- risk-free rate derived from the same price matrix

### 4. Parallelize across configurations

Process configurations independently using worker processes or an equivalent parallel execution model. This is the largest structural performance gain because configurations do not depend on one another.

### 5. Preserve deterministic selection

Keep the lock-candidate selection rule stable so that parallel execution does not change which configuration becomes the final preferred result.

## Expected Impact

- Lower wall-clock runtime for the sweep
- Less duplicate simulation work
- Better scalability as the sweep space expands
- Same external output artifacts, with faster generation

## Risks

- Parallel execution can complicate logging and debugging
- Cache-key mistakes could cause incorrect reuse of results
- Fast gating must not replace full validation; it can only short-circuit obvious failures
- Any change to execution order must preserve deterministic final selection

## Success Criteria

- The sweep still produces the same artifact set
- Valid configurations still pass the same acceptance logic
- Runtime is reduced measurably on the current dataset
- Final locked configuration selection remains deterministic
- Stress-test outputs remain available for accepted candidates
