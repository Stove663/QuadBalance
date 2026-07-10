## Why

The backtest engine applies a uniform 0.1% transaction cost to every buy and sell, but locked strategy instruments have materially different purchase fees (0%–0.12% after platform discounts). This systematically misstates costs for the cash quadrant (overcharged), bond/gold legs (overcharged), and QDII backup routing (wrong rate when 050025 or 006075 fills). Per-fund fees are a P1 execution-fidelity gap; this change implements Scheme A v1 (static per-symbol purchase rates, zero redemption for long-hold assumptions) after the rebalance shortfall fix lands.

## What Changes

- Add machine-readable `TradeFees` rates to the instrument pool for all symbols used in simulation (primaries + QDII backups)
- Replace uniform `TRANSACTION_COST` in `_buy` / `_sell` with per-symbol fee lookup via a `fees` module
- Apply the actual traded symbol's purchase rate on QDII backup routing (161125 → 050025 → 006075)
- Sync benchmark simulations to use the same per-symbol purchase fees
- Document fee assumptions in strategy-lock.md and deprecate the global `TRANSACTION_COST` constant for simulation paths
- Re-run full validation sweep; acceptance criteria thresholds unchanged

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `portfolio-backtest`: Require per-symbol purchase fee lookup on all buy/sell paths; document fee assumptions in output
- `asset-universe`: Require machine-readable trade fee rates on instruments used in backtest simulation

## Impact

- `src/quadbalance/fees.py` (new) — fee schedule and lookup
- `src/quadbalance/instrument_pool.py` — add numeric `TradeFees` alongside display strings
- `src/quadbalance/simulator.py` — replace `cost_rate` parameter with symbol-based fee lookup
- `src/quadbalance/benchmarks.py` — per-symbol fees on benchmark buys
- `src/quadbalance/config.py` — remove or deprecate `TRANSACTION_COST` for simulation
- `src/quadbalance/validation.py` — fee assumptions table in strategy-lock.md
- `tests/` — fee lookup tests; update existing simulator tests for per-symbol expectations
