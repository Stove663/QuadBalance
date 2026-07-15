## Context

The project already computes drawdown-related metrics such as maximum drawdown and underwater duration, but it does not yet expose a NAV recovery-time measure as a first-class risk constraint. The change adds a new risk dimension for long-horizon portfolio evaluation: how long the equity curve needs to return to the prior peak after the worst drawdown.

The implementation must fit the existing architecture, where `metrics` computes reusable performance statistics and `validation` applies acceptance gates. The stakeholder goal is to keep the metric explainable in reports while making the acceptance rule unambiguous and enforceable.

## Goals / Non-Goals

**Goals:**
- Compute NAV-based recovery time from the realized equity curve.
- Expose the value through metrics so it can be reported and inspected.
- Enforce a hard maximum recovery-time threshold in validation.
- Preserve existing backtest semantics and result formats wherever possible.
- Keep the rule deterministic and easy to test.

**Non-Goals:**
- Changing trade simulation logic or portfolio construction.
- Replacing existing drawdown or underwater metrics.
- Adding a second recovery definition based on contribution-adjusted wealth.
- Introducing new third-party dependencies.

## Decisions

1. **Store the value in `metrics`, enforce the rule in `validation`**

   The recovery-time number is a measurement, so it belongs with other derived statistics in `metrics`. The pass/fail policy is business logic, so it belongs in `validation`. This separation keeps the metric reusable in reports, rankings, and future rules.

   Alternatives considered:
   - Put the metric only in validation: simpler short-term, but prevents reuse and obscures the actual value in reports.
   - Put the rule only in metrics: mixes measurement with policy and weakens the acceptance layer.

2. **Define recovery relative to the peak preceding the maximum drawdown**

   The metric will measure the trading-day distance from the pre-drawdown peak to the first day the NAV recovers to that peak or higher. This matches the intuitive meaning of "how long did it take to get back to even after the worst drawdown?"

   Alternatives considered:
   - Measure from the trough to recovery: useful, but less directly tied to the investor experience of losing a prior peak.
   - Measure the longest recovery across all drawdowns: broader, but harder to explain and not aligned with the requested hard gate.

3. **Treat unrecovered paths as failing the hard gate**

   If the equity curve never returns to the pre-drawdown peak by the end of the test window, the configuration should fail validation. The metric can still report the unrecovered state for transparency.

   Alternatives considered:
   - Ignore unrecovered paths: would let slow-recovery strategies pass despite incomplete repair.
   - Impute a capped recovery time: less transparent and can hide the true risk.

4. **Expose the threshold as an explicit configuration constant or validation parameter**

   The threshold should be easy to locate and tune without modifying the metric computation code. This supports future governance changes while keeping the calculation stable.

   Alternatives considered:
   - Hardcode the threshold inside the metric function: makes the value less reusable.
   - Derive the threshold from a profile system immediately: more flexible, but unnecessary for the initial change.

## Risks / Trade-offs

- [Metric definition ambiguity] → Document the peak-to-recovery definition clearly and test against known curves.
- [Unrecovered end-of-window cases] → Mark them as validation failures while still exposing the metric value.
- [Extra computation cost] → Reuse the existing NAV series already produced by simulation rather than recomputing the equity curve.
- [Policy rigidity] → Keep the threshold centralized so future changes are simple and auditable.

## Migration Plan

1. Add the new recovery-time metric computation to the metrics layer.
2. Extend validation to consume the metric and enforce the hard maximum.
3. Update reporting outputs so the recovery time is visible in the lock document or summary tables.
4. Add regression tests for both a recovered and unrecovered path.
5. Run the full test suite and a representative backtest to confirm no unintended behavioral changes.

Rollback strategy:
- If the new rule causes unexpected strategy exclusions, lower or disable the validation threshold while preserving the metric output.
- If the metric calculation is incorrect, revert the new metric and validation wiring without changing the rest of the simulation pipeline.

## Open Questions

- What exact maximum recovery duration should be used as the initial hard gate?
- Should the metric be reported in trading days only, or also converted into calendar years for human readability?
- Should the validation failure message distinguish between "too slow" and "never recovered" cases?
