## Why

QDII quota simulation added backup funds (050025, 006075) to `ALL_SYMBOLS`, forcing `load_price_matrix()` to align all columns with `dropna(how="any")`. Because 006075 listed on 2018-06-08, the effective backtest start regressed from 2013-07-29 to 2018-06-08—losing ~5 years of history including 2015 and 2018 stress years. Backup instruments are tradable only on certain dates and must not define the global price-matrix alignment window.

## What Changes

- Split **price-matrix alignment symbols** (primaries + proxy-stitched columns) from **tradable backup symbols** (QDII backups loaded separately)
- Load QDII backup prices independently; join at simulation runtime only when the instrument is available on that date
- Introduce **date-aware QDII pool**: exclude 006075 before its inception; exclude independent 050025 routing before 161125 handoff
- Disable QDII daily quota enforcement during the 161125 proxy era (pre-handoff), when the primary column uses stitched 050025 NAV
- Change `dropna(how="any")` to apply only to alignment symbols, not backup columns
- Report effective start date, QDII pool era boundaries, and pre/post comparison in validation output
- Re-run full validation sweep after fix; acceptance criteria thresholds unchanged

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `portfolio-backtest`: Price-matrix alignment vs tradable-symbol sets; lazy backup price join; date-gated QDII pool and proxy-era quota rules
- `asset-universe`: Document inception dates and backup eligibility rules for QDII pool members
- `strategy-validation`: Require reporting of restored backtest period and era-segment metrics after matrix fix

## Impact

- `src/quadbalance/config.py` — `PRICE_MATRIX_SYMBOLS` vs `QDII_BACKUP_SYMBOLS`; remove backups from `ALL_SYMBOLS` alignment
- `src/quadbalance/data.py` — `load_backup_prices()`; alignment-only `dropna`
- `src/quadbalance/instrument_pool.py` — inception dates; `qdii_pool_for_date()`
- `src/quadbalance/simulator.py` — runtime backup price join; date-gated pool; proxy-era quota bypass
- `src/quadbalance/sweep.py`, `validation.py` — report era boundaries and effective start
- `tests/` — matrix start date, date-gated routing, proxy-era quota behavior
- `output/` — sweep and strategy-lock regenerated with restored 2013-era start
- **Coordination**: Should land before or with `per-fund-transaction-fees` so fee schedule targets correct tradable symbol set
