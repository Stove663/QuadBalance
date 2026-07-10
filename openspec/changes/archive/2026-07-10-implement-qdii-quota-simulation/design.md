# Design: QDII quota simulation

## Overview

This change models QDII subscription limits as a backtest-only execution constraint. The simulator should first attempt to buy the primary QDII fund, then fall back to ranked backups, and finally keep any unfilled amount as pending cash.

## Key decisions

### 1. Per-fund daily caps

Each QDII instrument keeps its own simulated daily subscription cap. The default cap for 161125 is 100 CNY/day unless overridden in `StrategyConfig.qdii_daily_caps`. Backup QDII funds such as 050025 and 006075 use independent counters in simulation.

### 2. Ranked backup execution

When a QDII purchase exceeds the remaining quota of the primary fund, the simulator should continue through the ranked QDII pool in order. Any substitution must be recorded so the strategy log can explain the realized fill path.

### 3. Pending cash handling

Any portion of a QDII purchase that cannot be filled should remain as pending cash rather than being forced into a different quadrant. This keeps the annual rebalance logic honest about execution friction and preserves visibility into quota-constrained capital.

### 4. Validation metrics

The simulation result should expose at least:

- QDII fill rate
- average pending cash
- maximum pending cash
- number of days with pending cash
- average QDII weight gap vs target
- substitution events

These metrics are sufficient for lock-document reporting and stress scenario comparison.

## Notes on simplification

Live trading may involve shared platform quota across multiple QDII products, but the backtest can use conservative independent caps per fund. That simplification is acceptable as long as it is explicitly documented in the spec and design.
