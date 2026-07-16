## Why

The current validation suite includes one-year macro shocks and a five-year low-rate path, but it does not explicitly model a multi-decade China "Japanification" regime with low growth, low rates, deflation risk, and balance-sheet recession dynamics. Investors using the strategy need to know whether a candidate allocation remains mechanically acceptable when historical growth and mean-reversion assumptions fail for 20-30 years.

## What Changes

- Add a long-horizon macro regime stress model for long-term stagflation, deflation, and balance-sheet recession scenarios.
- Introduce deterministic path simulations that generate synthetic annual return paths for each quadrant and CPI over 20-30 years.
- Report nominal return, real return, maximum drawdown, underwater duration, purchasing-power preservation, and withdrawal/depletion outcomes for each long-term scenario.
- Add strategy lock document sections summarizing long-term regime stress results separately from existing short-horizon S1-S12 stress tests.
- Add validation/governance rules that classify long-term regime results as normal, review-required, or thesis-broken without silently optimizing the allocation.
- No breaking changes to existing CLI options or existing S1-S12 stress semantics.

## Capabilities

### New Capabilities

- `long-term-macro-regime-stress`: Defines deterministic long-horizon stress models for stagflation, deflation, and balance-sheet recession, including path metrics and reporting requirements.

### Modified Capabilities

- `strategy-validation`: Extends validation and strategy-lock requirements so locked configurations include long-term macro regime stress summaries and governance classifications.

## Impact

- Affected modules: `src/quadbalance/stress.py`, `src/quadbalance/stress_scenarios.py`, `src/quadbalance/validation.py`, `src/quadbalance/reporting.py`, `src/quadbalance/reporting_sections.py`, and `src/quadbalance/sweep.py`.
- Affected outputs: `output/strategy-lock.md`, run artifacts, and potentially additional CSV/JSON artifacts for long-term regime paths.
- Affected tests: add unit tests for scenario path construction, real-return metrics, governance classification, and report rendering.
- No new third-party dependency is expected; deterministic synthetic paths should use existing Python, pandas, and project simulation primitives.
