## 1. Scenario Model and Path Generation

- [x] 1.1 Add long-term stress dataclasses for scenario assumptions, path results, metric summaries, and governance classifications.
- [x] 1.2 Define default LT1 prolonged stagflation, LT2 deflationary stagnation, and LT3 balance-sheet recession / Japanification scenarios with documented annual assumptions.
- [x] 1.3 Implement deterministic annual-to-daily synthetic price path generation for each quadrant and CPI path.
- [x] 1.4 Add instrument-to-quadrant path mapping with explicit recording of applied assumptions and overrides.

## 2. Simulation and Metrics

- [x] 2.1 Run locked configurations through generated long-term synthetic paths using the existing portfolio simulation engine.
- [x] 2.2 Compute nominal cumulative return, nominal annualized return, real cumulative return, real annualized return, real terminal wealth, maximum drawdown, and longest underwater duration.
- [x] 2.3 Compute worst rolling 5-year and 10-year real returns when horizon length supports those windows.
- [x] 2.4 Implement purchasing-power preservation and optional withdrawal/depletion checks.

## 3. Governance Classification

- [x] 3.1 Centralize default thresholds for normal, review-required, and thesis-broken long-term regime outcomes.
- [x] 3.2 Implement deterministic classification and threshold reason generation for each long-term scenario.
- [x] 3.3 Integrate long-term classifications with existing strategy boundary summary without changing sweep ranking logic.

## 4. Reporting and Artifacts

- [x] 4.1 Add `Long-Term Macro Regime Stress` section to `strategy-lock.md` with scenario assumptions and summary metrics.
- [x] 4.2 Persist long-term macro stress summary artifacts including scenario IDs, assumptions, metrics, classifications, and threshold reasons.
- [x] 4.3 Optionally persist detailed annual or daily synthetic path artifacts when generated.
- [x] 4.4 Ensure existing S1-S12 stress summary remains separate and unchanged.

## 5. Integration

- [x] 5.1 Invoke long-term regime stress only after final locked configuration selection.
- [x] 5.2 Pass long-term results through `run_sweep`, reporting, and artifact-writing call paths.
- [x] 5.3 Keep CLI behavior backward compatible with existing `quadbalance` options.

## 6. Tests and Validation

- [x] 6.1 Add tests for default scenario catalog availability and assumption documentation.
- [x] 6.2 Add tests for deterministic synthetic path generation length, compounding, and quadrant mapping.
- [x] 6.3 Add tests for real-return, drawdown, underwater, and rolling-window metrics.
- [x] 6.4 Add tests for governance classification threshold boundaries.
- [x] 6.5 Add tests for strategy lock rendering and artifact emission.
- [x] 6.6 Run `uv run pytest` and a representative `uv run quadbalance --output output --no-cache` validation pass.
