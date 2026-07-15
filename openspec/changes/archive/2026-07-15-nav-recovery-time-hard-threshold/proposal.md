## Why

The portfolio already tracks underwater behavior, but the existing metrics do not directly express how long it takes a strategy to recover its net asset value after the worst drawdown. For long-horizon investors, recovery speed is a critical risk dimension: a shallow drawdown that takes years to repair can be more damaging than a deeper drawdown that heals quickly.

This change adds a NAV-based recovery-time constraint so strategy selection can reject portfolios that are too slow to recover from their worst equity curve decline.

## What Changes

- Define a NAV-based recovery-time metric that measures the number of trading days required for the equity curve to reclaim the peak preceding the maximum drawdown.
- Treat the recovery-time limit as a hard validation gate rather than a purely informational metric.
- Surface the metric in reporting so the decision is explainable, while keeping acceptance logic in validation.

## Recommendation: Metrics vs Validation

Use **both**, but with different responsibilities:

- **metrics** should compute and expose the recovery-time value so it can be reported, ranked, and inspected.
- **validation** should enforce the threshold as a hard pass/fail rule.

In other words, the source value belongs in metrics, but the policy belongs in validation. This keeps the calculation reusable without coupling it to one specific acceptance rule.

## Capabilities

### New Capabilities
- `nav-recovery-time-metric`: compute NAV-based recovery duration from the equity curve.
- `nav-recovery-time-validation`: enforce a hard maximum recovery duration during strategy acceptance.

## Impact

This change affects the metric computation layer, acceptance checks, and reporting outputs that summarize core strategy risk characteristics. It should not change trade simulation behavior, but it may cause some currently passing configurations to fail validation if their recovery time exceeds the new threshold.
