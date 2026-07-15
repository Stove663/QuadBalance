## 1. Metric computation

- [x] 1.1 Add a NAV-based recovery-time calculation that measures days from the pre-drawdown peak to the first recovery date.
- [x] 1.2 Ensure unrecovered paths are represented explicitly so downstream code can distinguish them from successful recoveries.
- [x] 1.3 Surface the metric in the core metrics output used by reports and strategy summaries.

## 2. Validation and reporting

- [x] 2.1 Add a hard validation gate that fails strategies whose recovery time exceeds the configured maximum.
- [x] 2.2 Update acceptance and reporting flows so the recovery-time value and failure reason are visible in outputs.
- [x] 2.3 Confirm the metric remains reusable by keeping the calculation in metrics and the pass/fail policy in validation.

## 3. Tests and rollout

- [x] 3.1 Add regression tests for recovered and unrecovered equity curves.
- [x] 3.2 Update any lock-document or summary expectations to include the new recovery-time field.
- [x] 3.3 Run the full test suite and a representative backtest to verify the new hard gate behaves as intended.
