## Context

QuadBalance simulates off-exchange fund purchases with a single `TRANSACTION_COST = 0.001` (0.1%) applied to every `_buy()` and `_sell()` call. Human-readable fee strings exist on `FundInstrument` in `instrument_pool.py` but are not machine-parseable. QDII quota simulation routes purchases across 161125, 050025, and 006075 with different discounted purchase rates. Rebalance shortfall handling (separate change) computes sell proceeds as `amount - shortfall(fee)` — per-fund fees must land after that change to avoid rework.

## Goals / Non-Goals

**Goals:**

- Static per-symbol purchase fee rates for all instruments in `simulation_symbols()`
- Zero redemption fee for v1 (assumes holdings > 30 days at annual rebalance; monthly DCA lots are mostly long-held)
- Fee lookup by actual traded symbol (especially QDII backup routing)
- Benchmark simulations use the same fee schedule as strategy runs
- Fee assumptions documented in strategy-lock.md

**Non-Goals:**

- Holding-period tiered redemption fees (FIFO lot tracking) — v2
- Management fee / sales service fee drag — already embedded in NAV
- Share-class switching (A vs C) during live execution — locked strategy uses A-class primaries
- Fee sensitivity sweep (±50%) — optional follow-up
- Changing acceptance criteria thresholds

## Decisions

### D1: `TradeFees` dataclass + `fees.py` lookup module

Add `TradeFees(purchase_rate: float, redemption_rate: float)` with rates as decimals (e.g. `0.0012` for 0.12%). Expose `purchase_fee_rate(symbol) -> float` and `redemption_fee_rate(symbol) -> float`. v1 sets `redemption_rate = 0.0` for all simulation symbols.

**Alternative considered:** Parse `purchase_fee` strings at runtime — rejected; fragile and untestable.

### D2: Fee data on `FundInstrument`

Extend `FundInstrument` with `trade_fees: TradeFees` field. Populate from documented 1-discount (一折) rates in the existing pool. Keep `purchase_fee` display string for strategy-lock instrument tables.

Primary rates (v1):

| Symbol | Purchase | Redemption |
|--------|----------|------------|
| 110020 | 0.12% | 0% |
| 161125 | 0.12% | 0% |
| 050025 | 0.10% | 0% |
| 006075 | 0% | 0% |
| 003358 | 0.06% | 0% |
| 003327 | 0.08% | 0% |
| 000216 | 0.06% | 0% |
| 006874 | 0% | 0% |

**Alternative considered:** Separate `FEE_SCHEDULE` dict in config.py — rejected; duplicates instrument pool and drifts from backup definitions.

### D3: Replace `cost_rate` parameter with symbol lookup inside `_buy` / `_sell`

Change signatures to `_buy(..., symbol, ...)` and `_sell(..., symbol, ...)` resolving fee internally via `purchase_fee_rate(symbol)` / `redemption_fee_rate(symbol)`. Remove `cost_rate` threading through 20+ call sites.

**Alternative considered:** Pass resolved rate at each call site — rejected; error-prone, especially in QDII routing loops.

### D4: QDII premium remains separate from purchase fee

`qdii_premium` (S5 stress) multiplies price before fee: `effective_price = price * (1 + premium) * (1 + purchase_fee)`. Fees and premium are independent cost layers.

### D5: Benchmark fee alignment

`benchmarks.py` uses `purchase_fee_rate(symbol)` for single-asset and weighted benchmark buys. Redemption assumed 0% (buy-and-hold with contributions, minimal sells).

### D6: Reporting

Add "Transaction Fee Assumptions" section to strategy-lock.md listing purchase rate per primary instrument. Note v1 assumption: redemption 0% for long-hold.

### D7: Deprecate `TRANSACTION_COST`

Keep constant temporarily as fallback only if symbol missing from schedule (should not happen for simulation symbols). Log or raise in tests if lookup misses.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| v1 underestimates redemption cost on same-day DCA + rebalance | Document assumption; v2 adds holding-period tiers |
| Fee changes shift sweep metrics vs prior runs | Expected; re-run and note in archive — not a regression |
| 006874 at 0% reduces cost vs old 0.1% for QDII pending-cash parking | More accurate; may slightly improve returns |
| Missing fee for proxy symbols (518880, 161119, 070009) | Proxies are price-only; simulation trades primary symbols — no action needed |

## Migration Plan

1. Land `fix-rebalance-shortfall` first (or ensure merged)
2. Add `TradeFees` to instrument pool + `fees.py`
3. Refactor `_buy` / `_sell` and all call sites
4. Update benchmarks and tests
5. Re-run `uv run quadbalance`; compare sweep metrics to prior baseline
6. Archive change and sync spec deltas

## Open Questions

- None blocking v1. Fee sensitivity sweep deferred to optional follow-up change.
