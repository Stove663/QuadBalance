# Tasks: Add Drawdown and Stress-Gap Coverage

## 1. Scenario design and taxonomy

- [x] Define the new S22-S27 scenario IDs and risk themes.
- [x] Map each new scenario to the existing S13-S21 gaps it closes.
- [x] Separate path-dependence scenarios from execution-friction scenarios.
- [x] Specify which scenarios are nominal-only, real-return-aware, or both.
- [x] Document how each scenario should affect classification and reporting.

## 2. Stress engine and reporting

- [x] Add correlation-convergence and pseudo-diversification stress construction.
- [x] Add recovery-friction prolongation stress construction.
- [x] Add QDII routing-delay and FX-plus-quota stress construction.
- [x] Add rebalance-under-cross-border-stress construction.
- [x] Emit nominal and CPI-adjusted results for the new scenario family.
- [x] Surface longest underwater duration and recovery-time sensitivity in the report.

## 3. Product-risk escalation

- [x] Promote product-concentration risk into boundary summaries.
- [x] Report the dominant product-level contributor and reason.
- [x] Ensure implementation-risk escalation is visible in strategy-lock output.

## 4. Validation artifacts

- [x] Add an uncovered-risk summary section to the validation report.
- [x] Add the new scenarios to lock-document stress summaries when present.
- [x] Preserve existing S1-S21 outputs without changing their semantics.

## 5. Verification

- [x] Add unit tests for S22-S27 scenario taxonomy and mapping.
- [x] Add unit tests for cross-border stress result wiring in validation.
- [x] Add unit tests for uncovered-risk summary text coverage.
- [x] Add report snapshot coverage for the uncovered-risk summary.
- [x] Verify the new change integrates cleanly with existing strategy-validation specs.
- [x] Run the targeted test suite in a stable Python environment and confirm no regressions.
