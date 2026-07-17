# Proposal: Add Drawdown and Stress-Gap Coverage

## Summary

Add a new validation change set that closes the remaining portfolio drawdown and stress-test gaps identified during review. This change extends the existing strategy-validation framework with explicit path-dependence, recovery-friction, multi-asset correlation, cross-border execution, product-concentration, and real-value preservation checks so the locked strategy can be evaluated against the most failure-prone conditions that are not yet represented as first-class scenarios.

## Motivation

The current validation suite already covers primary backtest performance, benchmark comparison, short-horizon stress scenarios (S1-S21), extended macro boundary checks, lifecycle cashflow tests, and product-level implementation risk. However, several failure modes remain only partially represented or are spread across unrelated checks:

- Path dependence and recovery-friction risk, where the same terminal return can produce very different drawdown and recovery outcomes.
- Correlation convergence and “pseudo-diversification” risk, where defensive assets fail together over extended windows.
- Product concentration risk, where one sleeve can carry disproportionate implementation risk even if the total portfolio looks balanced.
- Cross-border and FX settlement friction, especially for QDII sleeves under quota pressure, premium/discount spread widening, and delayed routing.
- Real purchasing-power erosion, where nominal performance is acceptable but inflation-adjusted outcomes are not.
- Liquidity and rebalancing interaction, where the strategy cannot restore target weights at the moment the portfolio needs it most.

This change is intended to close the remaining validation gaps by turning those risks into explicit scenario families with clear reporting and classification. The new coverage complements, rather than replaces, the existing short-horizon and macro-regime tests.

## Goals

- Add dedicated stress coverage for correlation convergence, recovery-friction, and pseudo-diversification failure.
- Add explicit cross-border execution and FX-rebalance interaction stress cases.
- Add product-concentration and product-implementation escalation to the validation boundary set.
- Add clearer reporting for nominal vs real return deterioration and recovery-time sensitivity.
- Keep the locked allocation unchanged while improving validation fidelity and governance evidence.

## Non-Goals

- Do not redesign allocation weights as part of this change.
- Do not change primary strategy targets or quadrant weights.
- Do not rewrite the simulator unless a specific stress case requires a deterministic extension.
- Do not remove any existing stress scenario; this is additive coverage.

## Impact

This change will primarily affect the strategy-validation layer, the stress scenario catalog, and lock-document reporting. Some scenarios may also require small updates to lifecycle or simulator helpers if deterministic path construction is needed for new stress cases.
