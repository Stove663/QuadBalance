# Tasks

## 1. Specification

- [x] 1.1 Add project-scope requirements to `investment-strategy` for the three-phase roadmap.
- [x] 1.2 Add modularity requirements for data loading, configuration, simulation, metrics, suitability evaluation, and reporting.
- [x] 1.3 Add output-format requirements for CSV and markdown now, with JSON reserved for later GUI integration.
- [x] 1.4 Add investor-profile suitability requirements to `investment-strategy`.
- [x] 1.5 Add profile-aware allocation sweep and suitability reporting requirements to `strategy-validation`.
- [x] 1.6 Define required classifications: `suitable`, `caution`, `unsuitable`.
- [x] 1.7 Define strategy-lock disclosure requirements for profile suitability.

## 2. Configuration Model

- [x] 2.1 Add investor profile definitions and default thresholds.
- [x] 2.2 Expand allocation variants to include growth-tilted and preservation-tilted candidates.
- [x] 2.3 Ensure generated configuration IDs remain unique and comparable.
- [x] 2.4 Define the MVP profile set: accumulation, balanced core, pre-retirement preservation, retirement withdrawal.
- [x] 2.5 Define the MVP allocation comparison set for long-term accumulation and defensive protection.
- [x] 2.6 Document how profile thresholds map to `suitable`, `caution`, and `unsuitable`.
- [x] 2.7 Lock in MVP implementation defaults: daily backtest frequency, fixed-amount DCA, threshold-based rebalancing, and 15+ year backtest windows when available.
- [x] 2.8 Record the supported asset universe: QDII ETF, A-share ETF, Hong Kong ETF, domestic bond, QDII bond, gold, and cash.

## 3. Backtest and Stress Engine

- [x] 3.1 Preserve current historical backtest flow for the core engine.
- [x] 3.2 Add stress scenarios for bear market, high inflation, low growth, stagflation, and recession.
- [x] 3.3 Add scenarios for large drawdown recovery and DCA interruption.
- [x] 3.4 Make stress scenarios deterministic and comparable across configurations.
- [x] 3.5 Ensure backtest and stress outputs are reusable by suitability evaluation.

## 4. Lifecycle Simulation

- [x] 4.1 Replace value-curve post-processing lifecycle approximations with trade-level lifecycle simulation.
- [x] 4.2 Simulate DCA interruption by stopping future contributions while existing holdings continue to fluctuate.
- [x] 4.3 Simulate retirement withdrawal by selling assets or using cash according to deterministic rules.
- [x] 4.4 Simulate one-time liquidity need during drawdown.
- [x] 4.5 Include QDII quota, pending cash, fees, and rebalancing in lifecycle paths.

## 5. Suitability Evaluation

- [x] 5.1 Compute profile suitability for every candidate configuration.
- [x] 5.2 Include return, drawdown, real-return, lifecycle, behavioral, and execution-friction inputs.
- [x] 5.3 Emit human-readable reasons for each classification.
- [x] 5.4 Add suitability columns to sweep output.
- [x] 5.5 Ensure suitability evaluation is rule-based and deterministic.

## 6. Strategy Lock Document

- [x] 6.1 Add Investor Profile Suitability section.
- [x] 6.2 Include classification table and key reasons.
- [x] 6.3 State that suitability classification is a mechanical screen, not personalized financial advice.
- [x] 6.4 Preserve governance rule that allocation redesign requires a new validation run and lock document.

## 7. Tests and Validation

- [x] 7.1 Add tests for profile classification thresholds.
- [x] 7.2 Add tests for real lifecycle cashflow simulation.
- [x] 7.3 Add tests for expanded allocation variant generation.
- [x] 7.4 Ensure MVP pressure tests include recession and stagflation scenarios.
- [x] 7.5 Run OpenSpec validation for this change.
