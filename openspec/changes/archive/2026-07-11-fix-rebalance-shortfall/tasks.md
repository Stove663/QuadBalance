## 1. Simulator Core

- [x] 1.1 Add `RebalanceShortfallEvent` dataclass and `RebalanceExecutionMetrics` to simulator
- [x] 1.2 Refactor `_rebalance()` to track sell proceeds in a rebalance cash pool
- [x] 1.3 Capture `_sell()` shortfall return values and append to shortfall event log
- [x] 1.4 Cap underweight buy legs to available rebalance cash (proportional scaling when insufficient)
- [x] 1.5 Compute `max_post_rebalance_deviation` after each rebalance event
- [x] 1.6 Attach rebalance metrics and shortfall events to `SimulationResult`

## 2. Reporting

- [x] 2.1 Add rebalance execution columns to `SweepRow` and `sweep.py`
- [x] 2.2 Add Rebalance Execution section to `generate_lock_document()` in validation.py
- [x] 2.3 Include shortfall event detail when events > 0

## 3. Tests & Validation

- [x] 3.1 Add `tests/test_rebalance_shortfall.py` with synthetic zero-holding sell scenario
- [x] 3.2 Add test verifying buy legs capped when sell proceeds insufficient
- [x] 3.3 Add test verifying metrics populated on `SimulationResult`
- [x] 3.4 Run `openspec validate --change fix-rebalance-shortfall` and fix any errors
- [x] 3.5 Run full test suite and `uv run quadbalance` to verify sweep output
