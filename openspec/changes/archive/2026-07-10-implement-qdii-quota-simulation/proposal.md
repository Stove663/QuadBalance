# Change: Implement QDII quota simulation

## Why

The strategy now depends on QDII funds for the Stocks quadrant, but the current validation flow does not fully model daily subscription quota limits, backup fund switching, or the resulting pending cash behavior. This makes the backtest optimistic in quota-constrained scenarios and leaves strategy-lock documentation incomplete.

## What changes

- Add simulated daily QDII subscription caps for primary and backup funds.
- Route QDII purchases through a ranked backup pool when the primary fund hits quota limits.
- Track pending cash, fill rate, and substitution events in simulation output.
- Document the QDII execution behavior in strategy validation and strategy-lock outputs.
- Keep the live/default strategy aligned with the locked asset universe while allowing conservative backtest simplifications.

## Impact

- Backtests become more conservative and realistic for quota-constrained QDII purchases.
- Strategy validation can report QDII execution quality explicitly.
- The asset-universe and portfolio-backtest specs remain consistent with the locked instruments and backup policy.
