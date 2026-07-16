## Context

QuadBalance currently validates locked configurations with instantaneous stress shocks, execution-friction stress tests, and an S4 five-year low-rate path. Existing stress tests answer whether a portfolio survives short or medium shocks, but they do not model a structurally different 20-30 year macro regime where China experiences low growth, deflationary pressure, low rates, private-sector deleveraging, and weak risk appetite similar to Japan's lost decades.

The implementation should reuse the current simulation and reporting pipeline where practical. The new model must be deterministic and auditable, not a stochastic Monte Carlo engine, because strategy locks need reproducible governance evidence.

## Goals / Non-Goals

**Goals:**

- Add long-horizon synthetic path scenarios for:
  - prolonged stagflation,
  - deflationary stagnation,
  - balance-sheet recession / Japanification.
- Evaluate each path through the existing portfolio simulation mechanics where possible, including rebalancing, DCA, QDII quota behavior, fees, pending cash, and withdrawals where applicable.
- Report nominal and CPI-adjusted metrics: cumulative return, annualized return, real annualized return, maximum drawdown, longest underwater duration, worst rolling real return, and purchasing-power preservation.
- Classify each long-term regime result as `normal`, `review-required`, or `thesis-broken` using deterministic thresholds.
- Keep existing short-horizon stress scenario semantics unchanged.

**Non-Goals:**

- Build a probabilistic macro forecasting model or Monte Carlo simulator.
- Predict China's actual future growth, rates, currency path, or policy response.
- Automatically change allocation weights based on long-term stress outcomes.
- Replace the existing historical backtest or S1-S12 stress suite.

## Decisions

### 1. Introduce a separate long-term macro regime stress module

Create a new module, likely `long_term_stress.py`, rather than overloading `stress.py` with multi-decade path logic. `stress.py` can call into the module for orchestration, but scenario definitions and path metrics should live separately.

Rationale: existing `StressResult` is a compact one-row result for short stress tests. Long-term paths need richer output and should not force nullable fields into `StressResult`.

Alternatives considered:
- Extend `StressResult` with many optional fields: simpler initially, but obscures the distinction between short shock tests and long-horizon macro paths.
- Put everything in `stress_scenarios.py`: keeps definitions centralized, but mixes static one-year shocks with generated paths.

### 2. Model scenarios as deterministic annual assumptions expanded to synthetic daily price paths

Define each scenario as annual assumptions per quadrant plus CPI and optional currency/QDII friction assumptions. Convert the annual assumptions into daily return paths using deterministic compounding across the selected horizon, then run `simulate()` against the generated price matrix.

Rationale: reusing `simulate()` preserves actual portfolio mechanics instead of post-processing weights. It also keeps QDII quota, DCA, rebalancing, and fees consistent with existing behavior.

Alternatives considered:
- Weighted annual arithmetic calculation only: faster and easier, but misses rebalancing path dependency and execution friction.
- Historical Japan data grafting: realistic but introduces data sourcing and instrument mapping ambiguity.

### 3. Use named scenarios with explicit assumptions

Initial scenarios:

- `LT1 Prolonged stagflation`: 10-year high/volatile CPI regime with weak equities, negative real bonds, partial gold support, and low cash real return.
- `LT2 Deflationary stagnation`: 20-year low/negative CPI regime with weak equities, low nominal bond/cash returns, and muted gold.
- `LT3 Balance-sheet recession / Japanification`: 30-year regime with compressed equity returns, near-zero rates after initial bond rally, low/negative CPI, muted domestic risk assets, and reliance on overseas/gold diversification.

Rationale: separating scenarios allows users to distinguish inflationary policy failure from deflationary deleveraging and multi-decade balance-sheet recession.

### 4. Classify outcomes using governance thresholds, not acceptance optimization

A long-term regime should not automatically reject all otherwise valid strategies unless it breaches explicit thesis-broken thresholds. Suggested defaults:

- `normal`: real annualized return remains positive and purchasing power is preserved over the full horizon.
- `review-required`: real terminal wealth is below initial real wealth, real annualized return is negative, longest underwater duration exceeds 5 years, or withdrawal safety becomes questionable.
- `thesis-broken`: real terminal wealth loss exceeds 20%, rolling 10-year real return is below -10%, depletion occurs under a 4% withdrawal scenario, or underwater duration exceeds 10 years.

Rationale: long-term macro regimes are governance evidence. The engine should surface failure modes rather than silently select a different allocation.

### 5. Report paths separately from S1-S12

Add a `Long-Term Macro Regime Stress` section to `strategy-lock.md` with scenario assumptions, summary metrics, and classifications. If detailed paths are emitted, write `long_term_macro_stress.csv` or JSON under run artifacts.

Rationale: S1-S12 are short shock/execution tests. Combining them in one table would make the lock document harder to interpret.

## Risks / Trade-offs

- Synthetic path assumptions may appear overly precise → Mitigate by documenting assumptions in the report and treating outputs as scenario evidence, not forecasts.
- Multi-decade daily simulation could add runtime → Mitigate by only running long-term scenarios for the locked configuration, not every sweep candidate.
- Generated price paths may not map cleanly to all instruments → Mitigate by applying quadrant-level assumptions to every instrument in that quadrant, with explicit exceptions for QDII/currency-sensitive symbols if implemented.
- Deflation math can be confusing → Mitigate by reporting both nominal and real metrics and clearly showing CPI assumptions.
- Scenario thresholds may be subjective → Mitigate by making constants centralized and covered by tests.

## Migration Plan

1. Add dataclasses and deterministic path builders for long-term macro scenarios.
2. Add tests for scenario construction and path metrics.
3. Integrate the new long-term stress runner after locked configuration selection.
4. Add reporting sections and artifacts.
5. Re-run a full sweep and verify the locked document includes long-term results.
6. Rollback is straightforward: remove the new runner invocation and report section while preserving existing S1-S12 behavior.

## Open Questions

- Should long-term scenarios use default fixed assumptions only, or allow user-provided scenario JSON overrides later?
- Should overseas/QDII equity assumptions be represented separately from domestic stocks in phase one, or should phase one use quadrant-level approximations?
- Should long-term withdrawal stress be included in phase one, or added after core accumulation/no-withdrawal path metrics are stable?
