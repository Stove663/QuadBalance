## Why

The portfolio simulator's `_sell()` function returns a shortfall when holdings are insufficient to raise the target currency amount, but `_rebalance()` discards this return value. Rebalancing can therefore complete without raising enough cash to fund underweight buys, causing silent weight drift that is invisible in sweep output and strategy-lock reports. This is a P0 execution-fidelity gap identified during boundary review.

## What Changes

- Propagate sell shortfalls through the rebalance path and record them in simulation output
- Defer underweight buys when sell proceeds are insufficient, rather than assuming full execution
- Add rebalance execution metrics (shortfall events, unfulfilled buy amount, post-rebalance weight deviation)
- Include rebalance shortfall summary in sweep results and strategy-lock document
- Add unit tests covering insufficient-holdings rebalance scenarios

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `portfolio-backtest`: Add rebalance shortfall detection, handling, metrics, and reporting requirements to portfolio simulation

## Impact

- `src/quadbalance/simulator.py` — `_rebalance()`, `_sell()`, `SimulationResult`
- `src/quadbalance/sweep.py` — new columns in sweep output
- `src/quadbalance/validation.py` — strategy-lock rebalance execution section
- `tests/` — new rebalance shortfall test module
- `openspec/specs/portfolio-backtest/spec.md` — updated after archive via sync
