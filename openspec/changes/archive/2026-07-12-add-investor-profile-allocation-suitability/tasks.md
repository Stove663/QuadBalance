# Tasks

## 1. Specification

- [ ] 1.1 Add investor-profile suitability requirements to `investment-strategy`.
- [ ] 1.2 Add profile-aware allocation sweep and suitability reporting requirements to `strategy-validation`.
- [ ] 1.3 Define required classifications: `suitable`, `caution`, `unsuitable`.
- [ ] 1.4 Define strategy-lock disclosure requirements for profile suitability.

## 2. Configuration Model

- [ ] 2.1 Add investor profile definitions and default thresholds.
- [ ] 2.2 Expand allocation variants to include growth-tilted and preservation-tilted candidates.
- [ ] 2.3 Ensure generated configuration IDs remain unique and comparable.

## 3. Lifecycle Simulation

- [ ] 3.1 Replace value-curve post-processing lifecycle approximations with trade-level lifecycle simulation.
- [ ] 3.2 Simulate DCA interruption by stopping future contributions while existing holdings continue to fluctuate.
- [ ] 3.3 Simulate retirement withdrawal by selling assets or using cash according to deterministic rules.
- [ ] 3.4 Simulate one-time liquidity need during drawdown.
- [ ] 3.5 Include QDII quota, pending cash, fees, and rebalancing in lifecycle paths.

## 4. Suitability Evaluation

- [ ] 4.1 Compute profile suitability for every candidate configuration.
- [ ] 4.2 Include return, drawdown, real-return, lifecycle, behavioral, and execution-friction inputs.
- [ ] 4.3 Emit human-readable reasons for each classification.
- [ ] 4.4 Add suitability columns to sweep output.

## 5. Strategy Lock Document

- [ ] 5.1 Add Investor Profile Suitability section.
- [ ] 5.2 Include classification table and key reasons.
- [ ] 5.3 State that suitability classification is a mechanical screen, not personalized financial advice.
- [ ] 5.4 Preserve governance rule that allocation redesign requires a new validation run and lock document.

## 6. Tests and Validation

- [ ] 6.1 Add tests for profile classification thresholds.
- [ ] 6.2 Add tests for real lifecycle cashflow simulation.
- [ ] 6.3 Add tests for expanded allocation variant generation.
- [ ] 6.4 Run OpenSpec validation for this change.
