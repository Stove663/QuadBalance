# Proposal: Add Strategy Boundary Governance

## Summary

Add explicit strategy-level failure boundaries and governance rules to the QuadBalance validation process. This change extends validation beyond historical nominal performance and execution mechanics, so the strategy can answer when the investment thesis should be considered normal, review-required, or thesis-broken.

## Motivation

The current validation suite covers primary backtest performance, benchmark comparison, stress scenarios, QDII quota friction, transaction fees, proxy sensitivity, and rebalance execution quality. These are necessary but do not fully define when the strategy itself may fail from an investor perspective.

Important missing boundaries include:

- Macro regimes where diversification breaks down, such as stagflation, global liquidity shocks, CNY appreciation, or multi-quadrant stagnation.
- Lifecycle mismatches, such as DCA interruption, no-new-contribution periods, retirement withdrawals, and liquidity needs during drawdowns.
- Behavioral tolerance limits, such as long underwater periods or multi-year underperformance versus cash or 60/40 benchmarks.
- Real-return erosion, where nominal returns look acceptable but purchasing power is not preserved.
- Governance rules for deciding whether to continue, review, replace products, or redesign allocation weights.

Without these boundaries, a strategy can pass a historical backtest but still lack clear live-execution governance when market conditions or investor circumstances change.

## Goals

- Add real-return and rolling-window metrics to validation output.
- Add extended macro stress scenarios S8-S12.
- Add lifecycle cashflow stress tests for the locked strategy.
- Add behavioral review and thesis-broken trigger definitions.
- Add a strategy boundary report with normal / review-required / thesis-broken classifications.
- Add governance rules to prevent short-term parameter chasing and separate product replacement from allocation redesign.
- Require the strategy lock document to summarize boundary results and governance policy.

## Non-Goals

- Do not optimize allocation weights based on the new boundary tests in the same change.
- Do not automatically change the locked strategy when a review trigger fires.
- Do not replace primary instruments unless an existing product-governance rule says a replacement is required.
- Do not require historical CPI data as the only possible inflation source; documented annual CPI assumptions are acceptable for v1.

## Impact

This change affects the strategy-validation capability and output documents. Implementation will likely touch metrics calculation, stress-test orchestration, strategy-lock generation, and validation reporting. Lifecycle cashflow stress tests may require simulator support for contribution interruption and withdrawals.
