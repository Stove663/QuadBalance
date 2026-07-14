## Why

The current parameter sweep repeatedly runs expensive portfolio simulations for each candidate configuration. Every candidate runs the baseline simulation and a no-rebalance simulation, while candidates that pass fast validation also run additional full-stress simulations for S4, S5, and S7. This makes day-to-day iteration slow, especially as additional sweep dimensions such as stock sub-splits expand the candidate space.

We need a runtime optimization change that preserves final validation rigor while reducing unnecessary simulations during broad candidate exploration.

## What Changes

- Split sweep validation into staged evaluation so broad scans run baseline metrics and fast stress first, then full stress is applied only to shortlisted or lock-candidate configurations.
- Make no-rebalance premium calculation deferrable so most sweep candidates avoid the second baseline-like simulation unless the result is needed for candidate ranking, reporting, or final artifacts.
- Add an optional S4 window-scoped path evaluation mode so prolonged low-rate stress can avoid full-history simulation when path semantics allow a self-contained window test.
- Introduce an approximate stress mode for S5 and S7 during exploratory sweeps, while keeping exact rerun-based stress available for final validation and reports.
- Add simulation-result reuse for equivalent simulation requests within a sweep run to avoid recalculating baseline, no-rebalance, and stress variants that have already been computed.

## Capabilities

### New Capabilities
- `sweep-runtime-optimization`: Provide staged sweep evaluation modes, deferrable expensive metrics, optional approximate stress, S4 window-scoped evaluation, and simulation result reuse.

### Modified Capabilities
- `portfolio-backtest`: Allow reusable simulation execution and optional no-rebalance premium computation without changing default exact simulation semantics.
- `strategy-validation`: Distinguish exploratory candidate screening from final exact validation so only final candidates must pass complete stress validation.

## Impact

Affected areas include sweep orchestration, stress testing, metrics computation, simulation invocation, strategy-lock generation, and tests. The default final validation output must remain exact and auditable. Runtime modes may trade exploratory precision for speed, but final selected strategies must still be validated with exact stress tests unless explicitly configured otherwise.
