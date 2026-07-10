## 1. Fee Data Model

- [x] 1.1 Add `TradeFees` dataclass to `instrument_pool.py` with `purchase_rate` and `redemption_rate`
- [x] 1.2 Populate `trade_fees` on all simulation symbols (110020, 161125, 050025, 006075, 003358, 003327, 000216, 006874)
- [x] 1.3 Create `src/quadbalance/fees.py` with `purchase_fee_rate(symbol)` and `redemption_fee_rate(symbol)` lookup
- [x] 1.4 Add unit tests for fee schedule coverage and lookup errors on unknown symbols

## 2. Simulator Integration

- [x] 2.1 Refactor `_buy` and `_sell` to resolve fees by symbol internally (remove `cost_rate` parameter)
- [x] 2.2 Update all simulator call sites (DCA, rebalance, QDII routing, pending cash parking)
- [x] 2.3 Verify QDII backup routing applies 050025/006075 fee rates, not primary rate
- [x] 2.4 Deprecate `TRANSACTION_COST` for simulation paths in `config.py`

## 3. Benchmarks & Reporting

- [x] 3.1 Update `benchmarks.py` to use per-symbol purchase fees
- [x] 3.2 Add Transaction Fee Assumptions section to `validation.py` strategy-lock generator
- [x] 3.3 Note v1 redemption 0% assumption in lock document

## 4. Tests & Validation

- [x] 4.1 Add `tests/test_fees.py` — purchase fee math per instrument (006874 zero, 110020 0.12%)
- [x] 4.2 Update `tests/test_qdii_quota.py` expectations for 006874 zero-fee cash parking
- [x] 4.3 Update `tests/test_rebalance_shortfall.py` if fee-aware proceeds change shortfall amounts
- [x] 4.4 Run `openspec validate --change per-fund-transaction-fees` and fix any errors
- [x] 4.5 Re-run `uv run quadbalance` and compare sweep metrics to prior baseline
