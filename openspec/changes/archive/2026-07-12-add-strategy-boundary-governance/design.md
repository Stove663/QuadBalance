# Design: Strategy Boundary Governance

## Overview

This change introduces a boundary-governance layer on top of the existing validation suite. The existing suite answers whether a configuration performs acceptably over the primary historical backtest and existing stress tests. The new layer answers a different question: under what macro, lifecycle, behavioral, or real-return conditions should the locked strategy be reviewed or considered structurally broken?

The boundary layer should run after primary validation passes. It should not silently optimize or mutate the locked allocation.

## Concepts

### Boundary classification

Each boundary check produces one of three classifications:

- `normal`: strategy behavior remains within expected tolerance.
- `review-required`: strategy still may be valid, but an explicit review is required before blindly continuing.
- `thesis-broken`: the strategy thesis may no longer hold; continued live execution requires full re-validation or documented risk-reduction action.

### Boundary categories

The validation suite should group boundary checks into four categories:

1. `macro_regime`: diversification failure, stagflation, currency reversal, global liquidity crisis, multi-quadrant stagnation.
2. `lifecycle`: no DCA, DCA interruption, retirement withdrawals, one-time liquidity needs.
3. `behavioral`: drawdown tolerance, underwater duration, consecutive benchmark underperformance, actual QDII exposure shortfall.
4. `real_return`: CPI-adjusted return, rolling real return, purchasing-power preservation.

## Data model

A future implementation can use a structure similar to:

```python
@dataclass
class BoundaryResult:
    boundary_id: str
    category: str
    classification: Literal["normal", "review-required", "thesis-broken"]
    metric_name: str
    metric_value: float | int | str
    threshold: float | int | str
    start_date: date | None = None
    end_date: date | None = None
    explanation: str = ""
```

The final strategy boundary report should aggregate these results and expose:

- worst classification overall;
- count by classification;
- results by category;
- top review-required and thesis-broken reasons;
- recommended governance action.

## Real-return metrics

Real-return metrics require a CPI series or documented CPI assumptions. For v1, the system may support either:

1. annual CPI input loaded from a local file or provider; or
2. scenario-level CPI assumptions embedded in stress definitions.

Nominal portfolio values should be converted to real values by deflating cumulative returns using the CPI series aligned to calendar periods.

Required outputs:

- CPI-adjusted annualized return;
- CPI-adjusted terminal wealth;
- worst rolling 1-year, 3-year, 5-year nominal returns;
- worst rolling 1-year, 3-year, 5-year real returns;
- longest underwater duration;
- rolling underperformance counts versus cash and 60/40.

## Extended macro stress scenarios

The macro stress layer adds S8-S12:

- S8 stagflation;
- S9 global liquidity shock;
- S10 CNY appreciation;
- S11 domestic inflation shock;
- S12 multi-year quadrant stagnation.

These should be reported separately from execution-friction scenarios because they evaluate investment-thesis robustness, not only trade execution.

## Lifecycle cashflow tests

Lifecycle tests should run only for the locked configuration, not for every parameter-sweep candidate in v1. They are intentionally expensive and should not be used for silent optimization.

Required tests:

- no-DCA holding period;
- DCA interruption for 12, 24, and 36 months;
- DCA interruption after drawdown exceeds 10%;
- retirement withdrawals of 3%, 4%, and 5% of initial value, inflation-adjusted annually;
- retirement start at worst historical drawdown window;
- one-time 20% withdrawal during an existing drawdown.

## Governance policy

Governance output must separate three decision paths:

1. Continue execution: used for normal conditions.
2. Review: used when trigger thresholds are exceeded, but no automatic allocation change is allowed.
3. Re-validate: used when thesis-broken triggers fire or when target allocation redesign is proposed.

Product replacement should not be treated as asset-allocation redesign if the replacement remains in the same quadrant and satisfies asset-universe criteria.

Allocation redesign requires a new validation run and new strategy lock document. A cooldown rule should prevent repeated short-term redesigns unless a thesis-broken trigger occurs.

## Implementation phases

### Phase 1: Metrics and governance MVP

- Add real-return and rolling-window metrics.
- Add underwater duration.
- Add behavioral trigger classification.
- Add strategy lock governance section.

### Phase 2: Macro boundary stress

- Add S8-S12 stress definitions.
- Add boundary report aggregation.
- Add lock document boundary summary.

### Phase 3: Lifecycle cashflow tests

- Add simulator support for DCA interruption and withdrawals.
- Add lifecycle stress output.
- Integrate lifecycle classification into boundary report.

## Open questions

- What CPI data source should be preferred for historical real-return metrics?
- Should review-required thresholds be configurable per investor risk profile?
- Should lifecycle withdrawal tests use initial portfolio value or rolling portfolio value for withdrawal base in all variants?
