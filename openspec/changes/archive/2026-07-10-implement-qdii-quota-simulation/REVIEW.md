# Final Review: implement-qdii-quota-simulation

**Reviewed:** 2026-07-10

## Spec ↔ Implementation

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Per-fund daily QDII caps (default 100 CNY) | ✓ | `config.py`, `instrument_pool.default_qdii_daily_caps()` |
| Ranked backup routing (161125 → 050025 → 006075) | ✓ | `simulator._buy_qdii_with_quota`, `test_primary_exhausted_routes_to_backup` |
| Pending cash ledger + next-day fill | ✓ | `simulator._process_qdii_backlog`, tests |
| Portfolio value includes pending cash | ✓ | `_portfolio_value(..., pending_cash)` |
| Five QDII metrics in sweep output | ✓ | `sweep_results.csv` columns |
| QDII Execution section in lock doc | ✓ | `output/strategy-lock.md` |
| S7 low-quota stress scenario | ✓ | `stress.py` |
| Main specs synced | ✓ | `openspec/specs/{portfolio-backtest,strategy-validation,asset-universe}/spec.md` |

## Tests

`uv run python -m pytest -q` → **11 passed**

## Locked Asset Universe Alignment

- Primary QDII: 161125 (unchanged)
- Backups: 050025, 006075 (in `STOCKS_QDII_POOL`, loaded when `enable_qdii_quota=True`)
- Live execution rules unchanged; quota is backtest-only constraint

## Validation Criteria

- Acceptance criteria 1–5 unchanged; QDII quota makes backtests more conservative
- Default cap (100 CNY/day) over long horizon still yields ~100% cumulative fill rate (backlog clears over time); S7 (10 CNY/day) shows severe under-investment (fill ~8%, impact −102%)

## Minor Notes (non-blocking)

1. **S7 pass flag** hardcoded `True` — intentional; S7 is informational, not in acceptance criterion 3 (S1–S6 only)
2. **backup_events** recorded in `SimulationResult` but not listed in lock doc; spec "strategy log" satisfied by simulation output
3. **Delta specs** archived at `openspec/changes/archive/2026-07-10-implement-qdii-quota-simulation/`; main specs already contain merged requirements

## Conclusion

Change is **consistent** with locked asset universe and validation criteria. Ready to archive.
