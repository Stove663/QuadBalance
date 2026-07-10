## Context

The simulator's `_sell()` returns unraised currency when available shares are insufficient, but `_rebalance()` ignores this return value. Sell legs complete "successfully" while buy legs still attempt full target amounts, producing silent weight drift. QDII buy shortfalls are already handled via pending cash; sell-side shortfalls during rebalance are not.

Current rebalance flow: sell overweight → buy underweight → buy QDII gap. No cash pool tracks actual proceeds from sells.

## Goals / Non-Goals

**Goals:**

- Propagate sell shortfalls through rebalance and prevent buys from exceeding available proceeds
- Record shortfall events with date, symbol, requested amount, and unraised amount
- Expose rebalance execution metrics in `SimulationResult`, sweep CSV, and strategy-lock document
- Add deterministic unit tests using synthetic prices with constrained holdings

**Non-Goals:**

- General T+1 settlement modeling (separate change)
- Per-fund transaction fees (separate change)
- Mid-year rebalance triggers (strategy spec unchanged)
- Changing acceptance criteria thresholds

## Decisions

### D1: Rebalance cash pool

During `_rebalance()`, accumulate actual sell proceeds in a `rebalance_cash` variable (starting from `extra_cash`). Each `_sell()` adds `amount - shortfall` to the pool. Buy legs consume from this pool; buys are capped at `min(needed, rebalance_cash)`.

**Alternative considered:** Retry rebalance next day — rejected; annual rebalance is single-day per spec.

### D2: Shortfall event log

Append to `SimulationResult.rebalance_shortfalls: list[RebalanceShortfallEvent]` with fields: date, symbol, requested_cny, raised_cny, shortfall_cny. Also increment a counter on `SimulationResult`.

### D3: Buy scaling when cash insufficient

When `rebalance_cash < total_buy_need`, buy each underweight instrument proportionally to its deficit share, not full target. QDII buy uses remaining pool after non-QDII buys (same order as today: non-QDII first, then QDII).

**Alternative considered:** Skip all buys — rejected; partial execution is more realistic.

### D4: Post-rebalance deviation metric

After rebalance, compute max absolute quadrant weight deviation from target. Store as `max_post_rebalance_deviation` in metrics. Useful even when no shortfall occurs (QDII quota may leave drift).

### D5: Sweep reporting

Add columns to `SweepRow`: `rebalance_shortfall_events`, `total_rebalance_shortfall_cny`, `max_post_rebalance_deviation`. Include a Rebalance Execution section in strategy-lock.md when shortfall events > 0 or max deviation > threshold.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Shortfalls rare in normal backtest — hard to validate on real data | Synthetic tests with zero-share holdings force shortfall paths |
| Cash pool changes rebalance outcomes vs prior runs | Expected; document as execution-fidelity fix, not regression |
| QDII pending cash + rebalance cash pool interaction | Rebalance sells add to pool; QDII unfilled still routes to existing pending-cash path |

## Migration Plan

1. Implement simulator changes behind existing rebalance path (no feature flag needed)
2. Add tests
3. Re-run `uv run quadbalance` — metrics columns added to CSV; core acceptance criteria unchanged
4. Archive change and sync spec delta

## Open Questions

- None blocking implementation. Threshold for highlighting deviation in lock doc: use rebalance threshold (±5%) as default.
