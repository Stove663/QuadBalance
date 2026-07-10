## 1. Symbol Sets & Data Layer

- [ ] 1.1 Add `PRICE_MATRIX_SYMBOLS` to `config.py` (primaries + bond B3 columns; exclude QDII backups)
- [ ] 1.2 Remove `QDII_BACKUP_SYMBOLS` from `ALL_SYMBOLS` alignment set
- [ ] 1.3 Implement `load_backup_prices()` in `data.py` with parquet cache
- [ ] 1.4 Update `load_price_matrix_with_meta()` to use `PRICE_MATRIX_SYMBOLS` for `dropna(how="any")`
- [ ] 1.5 Add test: matrix effective start ≤ 2013-08-01 with cached data

## 2. Inception Dates & Date-Aware Pool

- [ ] 2.1 Add inception date constants and `instrument_inception_dates()` in `instrument_pool.py`
- [ ] 2.2 Implement `qdii_pool_for_date(dt)` with proxy / primary+backup1 / full pool eras
- [ ] 2.3 Add `primary_qdii_handoff_date()` derived from BACKTEST_PROXIES or 161125 first NAV
- [ ] 2.4 Add tests for pool membership at dates before 2016-12-02, 2017, and 2019

## 3. Simulator Integration

- [ ] 3.1 Update `simulate()` to accept optional `backup_prices: dict[str, pd.Series]`
- [ ] 3.2 Build `day_prices` by merging core row with date-eligible backup prices
- [ ] 3.3 Replace `_qdii_symbols_in_prices` with `_qdii_symbols_for_date(dt, day_prices)`
- [ ] 3.4 Implement proxy-era quota bypass (skip caps when `dt < handoff_date`)
- [ ] 3.5 Restrict `dropna(how="any")` in simulate to core symbols only
- [ ] 3.6 Update `sweep.py` to load backup prices and pass to simulate

## 4. Reporting & Validation

- [ ] 4.1 Add QDII era boundaries section to `generate_lock_document()` in `validation.py`
- [ ] 4.2 Ensure `effective_start` in lock doc reflects restored date
- [ ] 4.3 Re-run full sweep (`uv run quadbalance`) and record pre/post effective_start comparison
- [ ] 4.4 Verify segment_metrics proxy_era dates align with restored start

## 5. Integration & Spec Sync

- [ ] 5.1 Run `openspec validate --change qdii-backup-price-matrix` and fix errors
- [ ] 5.2 Update existing QDII quota tests if simulate signature changes
- [ ] 5.3 Confirm no regression in QDII fill rate / backup routing tests post-handoff
